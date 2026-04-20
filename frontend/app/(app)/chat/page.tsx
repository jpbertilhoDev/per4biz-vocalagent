"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Mic } from "lucide-react";

import { useChatStore, buildHistoryFromMessages, type VoxCard, type MicState } from "@/lib/chat-store";
import { VoxCard as VoxCardComponent } from "@/components/vox-card";
import { MicButton } from "@/components/mic-button";
import { useMediaRecorder } from "@/lib/use-media-recorder";
import {
  postTranscribe,
  postPolish,
  postIntent,
  postChat,
  fetchTTS,
  type PolishContext,
} from "@/lib/voice-api";
import {
  emailsKeys,
  listEmails,
  getEmail,
  fetchEmailHeadlines,
  trashEmail,
  listCalendarEvents,
  createCalendarEvent,
  updateCalendarEvent,
  deleteCalendarEvent,
  searchContacts,
  type EmailListResponse,
  type EmailDetail,
  type HeadlineItem,
  type CreateEventPayload,
  type UpdateEventPayload,
} from "@/lib/queries";
import { apiFetch, ApiError } from "@/lib/api";
import { VoiceTelemetry } from "@/lib/voice-telemetry";
import { cn } from "@/lib/utils";

function useVoxRecorder() {
  const recorder = useMediaRecorder();
  const micStateRef = useRef<MicState>("idle");
  const [micState, setMicStateDirect] = useState<MicState>("idle");

  const setMicState = useCallback((s: MicState) => {
    micStateRef.current = s;
    setMicStateDirect(s);
  }, []);

  useEffect(() => {
    if (recorder.state === "recording" && recorder.isSilent && micStateRef.current === "listening") {
      setMicState("silence-detected");
    } else if (recorder.state === "recording" && !recorder.isSilent && micStateRef.current === "silence-detected") {
      setMicState("listening");
    }
  }, [recorder.isSilent, recorder.state, setMicState]);

  useEffect(() => {
    if (recorder.state === "stopping" && micStateRef.current !== "processing") {
      setMicState("processing");
    }
  }, [recorder.state, setMicState]);

  useEffect(() => {
    if (recorder.state === "error" && micStateRef.current !== "error") {
      setMicState("error");
    }
  }, [recorder.state, setMicState]);

  return { recorder, micState, setMicState };
}

export default function ChatPage() {
  const { messages, addVoxCard, addUserMessage, updateVoxCard } = useChatStore();
  const { recorder, micState, setMicState } = useVoxRecorder();
  const qc = useQueryClient();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [welcomeSent, setWelcomeSent] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  // Active voice-session telemetry. Created on mic tap, flushed after TTS
  // finishes (or on error). Threaded through every backend call so the
  // server sees X-Voice-Session-Id on transcribe/intent/chat/polish/tts.
  const telemetryRef = useRef<VoiceTelemetry | null>(null);
  const lastEmailRef = useRef<{ fromName: string; fromEmail: string; subject: string; body: string; id: string } | null>(null);
  // pendingReplyRef tracks "we are actively awaiting the user's reply dictation".
  // Different from lastEmailRef which is "most recently discussed email".
  // When set, the next voice input bypasses intent classification and is
  // treated as the body of the draft reply (routed to postPolish).
  const pendingReplyRef = useRef<{
    emailId: string;
    fromName: string;
    fromEmail: string;
    subject: string;
    body: string;
    armedAt: number;
  } | null>(null);
  const lastCalendarEventRef = useRef<{
    id: string;
    summary: string;
    start: string; // ISO
    end: string; // ISO
    location?: string;
  } | null>(null);
  // Pending calendar actions awaiting user Sim/Não confirmation.
  // Keyed by a uuid attached to the confirmation card's meta.pendingId.
  const pendingActionsRef = useRef<
    Map<
      string,
      | { type: "create"; payload: CreateEventPayload }
      | { type: "edit"; eventId: string; summary: string; changes: UpdateEventPayload }
      | { type: "delete"; eventId: string; summary: string }
      | { type: "email-trash"; emailId: string; subject: string; fromName: string }
    >
  >(new Map());

  const { data: emailData } = useQuery<EmailListResponse>({
    queryKey: emailsKeys.list(),
    queryFn: () => listEmails(),
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, micState]);

  useEffect(() => {
    if (!welcomeSent && emailData?.emails?.length !== undefined) {
      const count = emailData.emails.length;
      setWelcomeSent(true);
      if (!messages.some((m) => m.role === "vox")) {
        addVoxCard({
          type: "agenda-placeholder",
          title: "Olá! Sou o Vox.",
          content: count > 0
            ? `Tens ${count} email${count !== 1 ? "s" : ""} na caixa de entrada. Diz-me o que queres fazer — leio emails, crio eventos ou procuro contactos.`
            : "A caixa de entrada está vazia. Posso gerir a tua agenda e contactos. Diz-me o que precisas.",
          actions: count > 0 ? [{ label: "Ler emails recentes", action: "read-emails" }] : undefined,
        });
      }
    }
  }, [emailData?.emails?.length, welcomeSent, messages.length, addVoxCard]);

  // Pause all page audio/video elements so they don't mix with Vox TTS.
  // Returns a function to restore them after speaking.
  const mutePageAudio = useCallback((): (() => void) => {
    // Cancel any ongoing Web Speech API utterances
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

    // Pause all other <audio> and <video> elements on the page
    const mediaElements: HTMLMediaElement[] = [];
    if (typeof document !== "undefined") {
      document.querySelectorAll<HTMLMediaElement>("audio:not([data-vox]), video").forEach((el) => {
        if (!el.paused) {
          el.pause();
          mediaElements.push(el);
        }
      });
    }

    return () => {
      // Restore previously playing media
      mediaElements.forEach((el) => {
        el.play().catch(() => {});
      });
    };
  }, []);

  const playTTS = useCallback(async (text: string): Promise<void> => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ""; }
    if (audioUrlRef.current) { URL.revokeObjectURL(audioUrlRef.current); audioUrlRef.current = null; }

    const restoreAudio = mutePageAudio();
    setMicState("speaking");

    // Snapshot the active session so async callbacks below still see it
    // even if a new session takes the ref slot mid-playback.
    const telemetry = telemetryRef.current;

    const finishSession = (): void => {
      if (telemetry && telemetryRef.current === telemetry) {
        telemetryRef.current = null;
      }
      void telemetry?.flush();
    };

    try {
      const blob = await fetchTTS(text.slice(0, 4000), undefined, telemetry ?? undefined);
      if (blob.size < 100) {
        throw new Error(`TTS returned suspiciously small audio: ${blob.size} bytes`);
      }
      const url = URL.createObjectURL(blob);
      audioUrlRef.current = url;
      const audio = new Audio(url);
      audio.dataset.vox = "true"; // mark as Vox audio so mutePageAudio skips it
      audioRef.current = audio;
      let firstPlayMarked = false;
      audio.onplaying = () => {
        if (!firstPlayMarked) {
          telemetry?.mark("audio_first_play");
          firstPlayMarked = true;
        }
      };
      audio.onended = () => {
        setMicState("idle");
        URL.revokeObjectURL(url);
        audioUrlRef.current = null;
        restoreAudio();
        finishSession();
      };
      audio.onerror = () => {
        console.warn("[Vox] ElevenLabs audio playback error");
        setMicState("idle");
        URL.revokeObjectURL(url);
        audioUrlRef.current = null;
        restoreAudio();
        addVoxCard({
          type: "error",
          title: "Voz indisponível",
          content: "Falha ao reproduzir áudio do ElevenLabs.",
        });
        telemetry?.mark("audio_first_play", "error");
        finishSession();
      };
      await audio.play();
    } catch (err) {
      console.warn("[Vox] ElevenLabs TTS failed:", err);
      restoreAudio();
      addVoxCard({
        type: "error",
        title: "Voz indisponível",
        content: "ElevenLabs não respondeu. Verifica a ligação ou a chave da API.",
      });
      setMicState("idle");
      telemetry?.mark("tts_done", "error");
      finishSession();
    }
  }, [setMicState, addVoxCard, mutePageAudio]);

  const handleReadEmails = useCallback(async (count = 3) => {
    if (!emailData?.emails?.length) {
      addVoxCard({ type: "error", title: "Sem emails", content: "Não encontrei emails na caixa de entrada." });
      await playTTS("Não tens emails na caixa de entrada.");
      return;
    }

    const toRead = emailData.emails.slice(0, count);

    // Try to fetch LLM-generated executive headlines (one batched call).
    // On failure, fall back to the snippet-based rendering so Vox stays alive.
    let headlineById = new Map<string, HeadlineItem>();
    try {
      const { headlines } = await fetchEmailHeadlines(toRead.map((e) => e.id));
      headlineById = new Map(headlines.map((h) => [h.id, h]));
    } catch {
      // Headlines API failed — leave map empty, UI falls back to snippet below.
    }

    // Show cards for each email — headline replaces snippet when available.
    for (const email of toRead) {
      const fromLabel = email.from_name ?? email.from_email;
      const headline = headlineById.get(email.id)?.headline;
      addVoxCard({
        type: "email-read",
        title: fromLabel,
        content: headline ?? email.snippet ?? "",
        meta: {
          De: fromLabel,
          Hora: new Date(email.received_at).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" }),
        },
        actions: [
          { label: "Resumir", action: "summarize-one" },
          { label: "Ler completo", action: "tts-full" },
          { label: "Responder", action: "reply" },
        ],
      });
    }

    // Executive briefing TTS — "Três emails. João pede... Maria confirma... Qual abres?"
    // Uses headlines when the LLM call succeeded; otherwise falls back to sender+subject.
    const n = toRead.length;
    const countWord = n === 1 ? "Um email"
      : n === 2 ? "Dois emails"
      : n === 3 ? "Três emails"
      : n === 4 ? "Quatro emails"
      : n === 5 ? "Cinco emails"
      : n === 6 ? "Seis emails"
      : n === 7 ? "Sete emails"
      : n === 8 ? "Oito emails"
      : n === 9 ? "Nove emails"
      : n === 10 ? "Dez emails"
      : `${n} emails`;

    const briefs = toRead.map((email) => {
      const headline = headlineById.get(email.id)?.headline;
      if (headline) return headline;
      const sender = email.from_name ?? email.from_email.split("@")[0];
      const subject = email.subject || "sem assunto";
      return `${sender}: ${subject}`;
    });

    const voiceText = `${countWord}. ${briefs.join(". ")}. Qual abres?`;
    await playTTS(voiceText);
  }, [emailData?.emails, addVoxCard, playTTS]);

  const handleReplyToEmail = useCallback(async (emailId: string) => {
    try {
      const detail: EmailDetail = await getEmail(emailId);
      lastEmailRef.current = {
        fromName: detail.from_name ?? detail.from_email,
        fromEmail: detail.from_email,
        subject: detail.subject,
        body: detail.body_text,
        id: detail.id,
      };
      // Arm dictation mode: the next voice input becomes the draft body.
      pendingReplyRef.current = {
        emailId: detail.id,
        fromName: detail.from_name ?? detail.from_email,
        fromEmail: detail.from_email,
        subject: detail.subject,
        body: detail.body_text,
        armedAt: Date.now(),
      };

      addVoxCard({
        type: "transcription",
        title: `Responder a ${detail.from_name ?? detail.from_email}`,
        content: `Assunto: ${detail.subject}. Toca no microfone e dita a tua resposta.`,
        meta: { De: detail.from_name ?? detail.from_email, Assunto: detail.subject },
      });

      await playTTS(`Vais responder a ${detail.from_name ?? detail.from_email}. Dita a tua resposta.`);
    } catch {
      addVoxCard({ type: "error", title: "Erro", content: "Não consegui carregar o email para responder." });
    }
  }, [addVoxCard, playTTS]);

  // Called when voice input arrives while pendingReplyRef is armed:
  // route the transcript to /voice/polish with the email context and
  // show the polished draft as a card for explicit confirmation.
  const handleDictatedReply = useCallback(
    async (
      transcript: string,
      context: {
        emailId: string;
        fromName: string;
        fromEmail: string;
        subject: string;
        body: string;
      },
    ) => {
      try {
        const polishContext: PolishContext = {
          transcript,
          from_name: context.fromName,
          from_email: context.fromEmail,
          subject: context.subject,
          body: context.body,
        };
        const polished = await postPolish(polishContext, telemetryRef.current ?? undefined);

        addVoxCard({
          type: "draft",
          title: `Rascunho para ${context.fromName}`,
          content: polished.polished_text,
          meta: {
            Para: context.fromEmail,
            Assunto: `Re: ${context.subject}`,
          },
          actions: [
            { label: "Editar", action: "edit" },
            { label: "Ditar de novo", action: "redictate" },
            { label: "Enviar", action: "send" },
          ],
        });

        // Draft is now visible; user must explicitly tap Enviar (or say "enviar").
        pendingReplyRef.current = null;

        await playTTS("Pronto. Vê o rascunho e toca em Enviar quando estiver bem.");
      } catch {
        addVoxCard({
          type: "error",
          title: "Não consegui preparar o rascunho",
          content: "Tenta ditar novamente.",
          actions: [{ label: "Tentar de novo", action: "redictate" }],
        });
        await playTTS("Falhou. Tenta ditar novamente.");
      }
    },
    [addVoxCard, playTTS],
  );

  const processIntent = useCallback(async (transcript: string) => {
    let intentResult: { intent: string; params: Record<string, unknown> };

    // Build history from last 10 chat messages for multi-turn reference resolution.
    const history = buildHistoryFromMessages(messages);

    try {
      const result = await postIntent(transcript, history, telemetryRef.current ?? undefined);
      intentResult = { intent: result.intent, params: result.params };
    } catch {
      intentResult = { intent: "general", params: {} };
    }

    const intent = intentResult.intent;

    if (intent === "read_emails") {
      const count = Number(intentResult.params.count) || 3;
      await handleReadEmails(count);
    } else if (intent === "reply") {
      const lastEmail = emailData?.emails?.[0];
      if (lastEmail) {
        await handleReplyToEmail(lastEmail.id);
      } else {
        addVoxCard({ type: "error", title: "Sem email", content: "Não há email para responder." });
        await playTTS("Não há email para responder na caixa de entrada.");
      }
    } else if (intent === "send") {
      const lastDraft = [...messages].reverse().find((m): m is VoxCard & { role: "vox" } => m.role === "vox" && m.type === "draft");
      if (lastDraft) {
        handleCardAction("send", lastDraft.id);
      } else {
        addVoxCard({ type: "error", title: "Sem draft", content: "Não há draft para enviar. Dita primeiro a tua resposta." });
        await playTTS("Não tens nenhum draft para enviar. Dita primeiro a tua resposta.");
      }
    } else if (intent === "summarize") {
      const count = Number(intentResult.params.count) || 5;
      const emails = emailData?.emails?.slice(0, count) ?? [];
      if (emails.length === 0) {
        await playTTS("Não tens emails para resumir.");
        return;
      }
      const summary = emails.map((e, i) => `${i + 1}. De ${e.from_name ?? e.from_email}, ${e.subject}`).join(". ");
      addVoxCard({
        type: "email-read",
        title: `Resumo de ${emails.length} emails`,
        content: summary,
      });
      await playTTS(`Resumo dos teus ${emails.length} emails. ${summary}`);
    } else if (intent === "calendar_list") {
      try {
        const now = new Date().toISOString();
        const days = Number(intentResult.params.days) || 7;
        const timeMax = new Date(Date.now() + days * 86400000).toISOString();
        const calData = await listCalendarEvents(now, timeMax);
        const events = calData.events;
        if (events.length === 0) {
          addVoxCard({ type: "calendar-event", title: "Sem eventos", content: `Não tens compromissos nos próximos ${days} dias.` });
          await playTTS(`Não tens compromissos nos próximos ${days} dias.`);
        } else {
          for (const ev of events.slice(0, 5)) {
            const timeStr = ev.is_all_day
              ? "todo o dia"
              : `${new Date(ev.start).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}–${new Date(ev.end).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}`;
            addVoxCard({
              type: "calendar-event",
              title: ev.summary || "(sem título)",
              content: ev.description || timeStr,
              meta: {
                Quando: `${new Date(ev.start).toLocaleDateString("pt-PT", { weekday: "short", day: "numeric", month: "short" })}, ${timeStr}`,
                ...(ev.location ? { Onde: ev.location } : {}),
              },
            });
          }
          // Track the first listed event so "cancela essa" / "muda essa" resolves without LLM id.
          const first = events[0];
          lastCalendarEventRef.current = {
            id: first.id,
            summary: first.summary,
            start: first.start,
            end: first.end,
            location: first.location || undefined,
          };
          const voiceSummary = events.slice(0, 5).map((e) => `${e.summary} ${e.is_all_day ? "todo o dia" : `às ${new Date(e.start).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}`}`).join(". ");
          await playTTS(`Tens ${events.length} evento${events.length > 1 ? "s" : ""}. ${voiceSummary}`);
        }
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.detail === "calendar_scope_missing") {
            addVoxCard({
              type: "error",
              title: "Permissão em falta",
              content: "O scope do Google Calendar não foi concedido. Volta a autorizar.",
              actions: [{ label: "Autorizar agenda", action: "reauth" }],
            });
            await playTTS("Falta-me permissão para o calendário. Autoriza, por favor.");
          } else if (err.detail === "calendar_api_not_enabled") {
            addVoxCard({
              type: "error",
              title: "Calendar API desativada",
              content: "O administrador precisa ativar a Google Calendar API no Google Cloud Console (APIs & Services → Library).",
            });
            await playTTS("A Calendar API não está ativada no Google Cloud.");
          } else {
            addVoxCard({
              type: "error",
              title: `Erro ${err.status}`,
              content: err.detail,
            });
            await playTTS("Não consegui carregar a agenda.");
          }
        } else {
          addVoxCard({ type: "error", title: "Erro", content: "Não consegui carregar a agenda." });
          await playTTS("Não consegui carregar a agenda.");
        }
      }
    } else if (intent === "calendar_create") {
      const { summary, start, end, location, is_reminder } = intentResult.params as {
        summary?: string;
        start?: string;
        end?: string;
        location?: string;
        is_reminder?: boolean;
      };
      if (!summary) {
        const askTitle = is_reminder ? "Lembrete" : "Criar evento";
        const askMsg = is_reminder
          ? "Do que te queres lembrar?"
          : "Qual é o título do evento que queres criar?";
        addVoxCard({ type: "transcription", title: askTitle, content: askMsg });
        await playTTS(askMsg);
        return;
      }
      const now = new Date();
      const finalStart = start ?? new Date(now.getTime() + 3600000).toISOString();
      const reminderDurationMs = 5 * 60 * 1000;
      const defaultDurationMs = is_reminder ? reminderDurationMs : 3600000;
      const finalEnd =
        end ?? new Date(new Date(finalStart).getTime() + defaultDurationMs).toISOString();
      const payload: CreateEventPayload = {
        summary,
        start: finalStart,
        end: finalEnd,
        ...(location ? { location } : {}),
      };

      const pendingId = crypto.randomUUID();
      pendingActionsRef.current.set(pendingId, { type: "create", payload });

      const dateLabel = new Date(finalStart).toLocaleDateString("pt-PT", {
        weekday: "long",
        day: "numeric",
        month: "short",
      });
      const timeLabel = new Date(finalStart).toLocaleTimeString("pt-PT", {
        hour: "2-digit",
        minute: "2-digit",
      });
      const whenStr = is_reminder
        ? `${dateLabel}, ${timeLabel}`
        : `${dateLabel}, ${timeLabel}–${new Date(finalEnd).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}`;
      addVoxCard({
        type: "calendar-confirm",
        title: is_reminder ? "Criar lembrete?" : "Criar evento?",
        content: [summary, whenStr, location].filter(Boolean).join("\n"),
        meta: {
          ...(is_reminder ? { Lembrete: summary } : { Título: summary }),
          Quando: whenStr,
          ...(location ? { Onde: location } : {}),
          pendingId,
        },
        actions: [
          { label: "Cancelar", action: "calendar-cancel" },
          {
            label: is_reminder ? "Sim, lembrar" : "Sim, criar",
            action: "calendar-create-confirm",
          },
        ],
      });
      await playTTS(
        is_reminder
          ? `Queres que te lembre de ${summary}?`
          : `Queres que marque ${summary}?`,
      );
    } else if (intent === "calendar_edit") {
      const target = lastCalendarEventRef.current;
      if (!target) {
        addVoxCard({
          type: "error",
          title: "Qual evento?",
          content: "Não sei a que evento te referes. Pede-me primeiro a agenda, ou diz o nome do evento.",
        });
        await playTTS("Qual evento queres editar?");
        return;
      }

      const params = intentResult.params as {
        summary?: string;
        start?: string;
        end?: string;
        location?: string;
      };
      const changes: UpdateEventPayload = {};
      if (params.summary) changes.summary = params.summary;
      if (params.start) changes.start = params.start;
      if (params.end) changes.end = params.end;
      if (params.location) changes.location = params.location;

      if (Object.keys(changes).length === 0) {
        addVoxCard({
          type: "error",
          title: "O que queres mudar?",
          content: `No evento "${target.summary}" — indica-me o que queres alterar (hora, data, título, local).`,
        });
        await playTTS(`O que queres mudar no evento ${target.summary}?`);
        return;
      }

      const pendingId = crypto.randomUUID();
      pendingActionsRef.current.set(pendingId, {
        type: "edit",
        eventId: target.id,
        summary: target.summary,
        changes,
      });

      const previewMeta: Record<string, string> = { Evento: target.summary };
      if (changes.summary) previewMeta["Novo título"] = changes.summary;
      if (changes.start) {
        const newStart = new Date(changes.start);
        const newEnd = changes.end ? new Date(changes.end) : null;
        previewMeta["Nova hora"] = newEnd
          ? `${newStart.toLocaleDateString("pt-PT", { weekday: "long", day: "numeric", month: "short" })}, ${newStart.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}–${newEnd.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}`
          : `${newStart.toLocaleDateString("pt-PT", { weekday: "long", day: "numeric", month: "short" })}, ${newStart.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}`;
      }
      if (changes.location) previewMeta["Novo local"] = changes.location;
      previewMeta.pendingId = pendingId;

      addVoxCard({
        type: "calendar-confirm",
        title: `Alterar "${target.summary}"?`,
        content: "Confirmas as alterações abaixo?",
        meta: previewMeta,
        actions: [
          { label: "Cancelar", action: "calendar-cancel" },
          { label: "Sim, alterar", action: "calendar-edit-confirm" },
        ],
      });
      await playTTS(`Confirmas as alterações ao evento ${target.summary}?`);
    } else if (intent === "calendar_delete") {
      const target = lastCalendarEventRef.current;
      if (!target) {
        addVoxCard({
          type: "error",
          title: "Qual evento?",
          content: "Não sei a que evento te referes. Pede-me primeiro a agenda, ou diz o nome do evento a apagar.",
        });
        await playTTS("Qual evento queres apagar?");
        return;
      }

      const pendingId = crypto.randomUUID();
      pendingActionsRef.current.set(pendingId, {
        type: "delete",
        eventId: target.id,
        summary: target.summary,
      });

      const whenStr = `${new Date(target.start).toLocaleDateString("pt-PT", { weekday: "long", day: "numeric", month: "short" })}, ${new Date(target.start).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}`;
      addVoxCard({
        type: "calendar-confirm",
        title: `Apagar "${target.summary}"?`,
        content: "Esta ação não pode ser desfeita.",
        meta: {
          Evento: target.summary,
          Quando: whenStr,
          ...(target.location ? { Onde: target.location } : {}),
          pendingId,
        },
        actions: [
          { label: "Cancelar", action: "calendar-cancel" },
          { label: "Sim, apagar", action: "calendar-delete-confirm" },
        ],
      });
      await playTTS(`Confirmas que apago ${target.summary}?`);
    } else if (intent === "email_delete") {
      // Mirrors the calendar_delete flow: resolve target via lastEmailRef,
      // show a confirmation card with Sim/Cancelar, execute on confirm.
      // Never auto-trash — destructive action requires explicit user tap.
      const target = lastEmailRef.current;
      if (!target) {
        addVoxCard({
          type: "error",
          title: "Qual email?",
          content: "Não sei a que email te referes. Abre ou lê primeiro o email.",
        });
        await playTTS("Qual email queres apagar?");
        return;
      }

      const pendingId = crypto.randomUUID();
      pendingActionsRef.current.set(pendingId, {
        type: "email-trash",
        emailId: target.id,
        subject: target.subject,
        fromName: target.fromName,
      });

      addVoxCard({
        type: "email-confirm",
        title: "Apagar email?",
        content: `De ${target.fromName}\n${target.subject}`,
        meta: {
          De: target.fromName,
          Assunto: target.subject,
          pendingId,
        },
        actions: [
          // Reuse calendar-cancel — same semantics (remove pending + "Cancelei.")
          { label: "Cancelar", action: "calendar-cancel" },
          { label: "Sim, apagar", action: "email-delete-confirm" },
        ],
      });
      await playTTS(`Apago o email de ${target.fromName}?`);
    } else if (intent === "contacts_search") {
      const query = String(intentResult.params.query ?? transcript);
      try {
        const contactsData = await searchContacts(query);
        const contacts = contactsData.contacts;
        if (contacts.length === 0) {
          addVoxCard({ type: "contact-card", title: "Sem resultados", content: `Não encontrei contactos para "${query}".` });
          await playTTS(`Não encontrei contactos para ${query}.`);
        } else {
          for (const c of contacts.slice(0, 3)) {
            addVoxCard({
              type: "contact-card",
              title: c.display_name || c.emails[0] || "(sem nome)",
              content: c.emails.length > 0 ? c.emails.join(", ") : c.phones.join(", ") || "(sem contacto)",
              meta: {
                ...(c.organization ? { Empresa: c.organization } : {}),
                ...(c.title ? { Cargo: c.title } : {}),
              },
            });
          }
          const names = contacts.slice(0, 3).map((c) => c.display_name || c.emails[0]).join(", ");
          await playTTS(`Encontrei ${contacts.length} contacto${contacts.length > 1 ? "s" : ""}. ${names}.`);
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          addVoxCard({
            type: "error",
            title: "Permissão necessária",
            content: "Preciso de acesso aos teus Google Contacts. Faz login novamente para autorizar.",
            actions: [{ label: "Autorizar contactos", action: "reauth" }],
          });
          await playTTS("Preciso de acesso aos teus contactos. Toca em Autorizar contactos.");
        } else {
          addVoxCard({ type: "error", title: "Erro", content: "Não consegui procurar contactos." });
          await playTTS("Não consegui procurar contactos. Verifica a tua ligação.");
        }
      }
    } else {
      // General intent. If the classifier flagged ambiguity, ask the user to
      // repeat instead of inventing a chat reply — senior-secretary behaviour.
      if (intentResult.params.ask_clarification === true) {
        addVoxCard({
          type: "transcription",
          title: "Não percebi",
          content: "Podes repetir, com mais contexto?",
        });
        await playTTS("Não percebi. Podes repetir?");
        return;
      }

      // Normal general chat — respond intelligently via Vox LLM.
      try {
        // Build conversation history for context (last 10 messages)
        const history = buildHistoryFromMessages(messages);

        const chatResult = await postChat(transcript, history, telemetryRef.current ?? undefined);
        addVoxCard({
          type: "transcription",
          title: "Vox",
          content: chatResult.response_text,
        });
        await playTTS(chatResult.response_text);
      } catch {
        // Fallback only if chat endpoint fails
        addVoxCard({
          type: "transcription",
          title: "Vox",
          content: "Não consegui processar o pedido. Tenta de novo.",
        });
        await playTTS("Não consegui processar. Tenta de novo.");
      }
    }
  }, [emailData?.emails, messages, addVoxCard, handleReadEmails, handleReplyToEmail, playTTS]);

  const handleMicClick = useCallback(() => {
    if (micState === "idle") {
      // New voice session — flush any stale telemetry first (defensive)
      if (telemetryRef.current) {
        void telemetryRef.current.flush();
      }
      const t = new VoiceTelemetry();
      t.start();
      telemetryRef.current = t;
      recorder.start(2000);
      setMicState("listening");
    } else if (micState === "listening" || micState === "silence-detected") {
      recorder.stop();
    } else if (micState === "error") {
      recorder.reset();
      setMicState("idle");
    }
  }, [micState, recorder, setMicState]);

  useEffect(() => {
    if (recorder.state !== "ready" || !recorder.audioBlob) return;

    setMicState("processing");

    // Mark the VAD cut on the active telemetry session (if any) before
    // the upload kicks off, so upload_start/upload_done bracket the POST.
    telemetryRef.current?.mark("vad_cut");

    postTranscribe(recorder.audioBlob, telemetryRef.current ?? undefined)
      .then(async (result) => {
        const transcribedText = result.text;
        addUserMessage(transcribedText, true);

        // If we are awaiting a reply dictation, bypass intent classification
        // and route straight to draft creation. The classifier's history-based
        // detection is a second line of defense if this ref is unexpectedly
        // cleared (see voice_intent.py Regra #8).
        const pending = pendingReplyRef.current;
        if (pending) {
          // Safety: clear stale arms older than 10 min and fall back to normal flow.
          if (Date.now() - pending.armedAt > 10 * 60_000) {
            pendingReplyRef.current = null;
            return processIntent(transcribedText);
          }

          // Cancel words: user wants out of reply mode.
          const lower = transcribedText.toLowerCase().trim();
          const cancelWords = ["cancelar", "cancela", "deixa", "esquece", "esqueçe"];
          if (cancelWords.some((w) => lower.startsWith(w) || lower === w)) {
            pendingReplyRef.current = null;
            addVoxCard({
              type: "transcription",
              title: "Cancelado",
              content: "Ok, cancelei o rascunho.",
            });
            await playTTS("Cancelei.");
            return;
          }

          return handleDictatedReply(transcribedText, pending);
        }

        return processIntent(transcribedText);
      })
      .catch(() => {
        addVoxCard({ type: "error", title: "Erro ao processar", content: "Não foi possível processar a gravação. Tenta de novo.", actions: [{ label: "Tentar de novo", action: "retry" }] });
        // Flush on error path — playTTS won't be called here, so the session
        // would otherwise leak events on the client buffer.
        if (telemetryRef.current) {
          telemetryRef.current.mark("upload_done", "error");
          void telemetryRef.current.flush();
          telemetryRef.current = null;
        }
      })
      .finally(() => {
        setMicState("idle");
        recorder.reset();
      });
  }, [recorder.state, recorder.audioBlob]);

  const handleCardAction = useCallback((action: string, cardId: string) => {
    const card = messages.find((m): m is VoxCard & { role: "vox" } => m.role === "vox" && m.id === cardId);

    if (action === "read-emails") {
      handleReadEmails(3);
    }

    if (action === "tts" && card) {
      // Repeat what's already on the card — short.
      playTTS(card.content?.slice(0, 300) ?? card.title ?? "");
    }

    if ((action === "summarize-one" || action === "tts-full") && card?.meta?.De) {
      const email = emailData?.emails?.find((e) => (e.from_name ?? e.from_email) === card.meta!.De);
      if (email) {
        getEmail(email.id).then(async (detail: EmailDetail) => {
          lastEmailRef.current = {
            fromName: detail.from_name ?? detail.from_email,
            fromEmail: detail.from_email,
            subject: detail.subject,
            body: detail.body_text,
            id: detail.id,
          };

          // Ask the LLM for a 1-2 sentence executive summary instead of reading the whole email
          try {
            const result = await postChat(
              `Resume este email em 1-2 frases curtas, como um secretário executivo. Não leias verbatim, captura só o essencial.\n\nDe: ${detail.from_name ?? detail.from_email}\nAssunto: ${detail.subject}\nCorpo:\n${detail.body_text.slice(0, 3000)}`,
              [],
              telemetryRef.current ?? undefined,
            );
            addVoxCard({
              type: "email-read",
              title: `Resumo: ${detail.subject}`,
              content: result.response_text,
              meta: { De: detail.from_name ?? detail.from_email },
              actions: [{ label: "Responder", action: "reply" }],
            });
            playTTS(result.response_text);
          } catch {
            // Fallback: short snippet
            const snippet = detail.body_text.slice(0, 200);
            playTTS(`${detail.from_name ?? detail.from_email}: ${detail.subject}. ${snippet}`);
          }
        });
      }
    }

    if (action === "reply" && card?.meta?.De) {
      const email = emailData?.emails?.find((e) => (e.from_name ?? e.from_email) === card.meta!.De);
      if (email) {
        handleReplyToEmail(email.id);
      }
    }

    if (action === "send" && card?.type === "draft") {
      const lastEmail = lastEmailRef.current;
      const meta = card.meta ?? {};
      // Defensive: pending dictation is invalidated once send is attempted.
      pendingReplyRef.current = null;
      apiFetch("/emails/send", {
        method: "POST",
        body: JSON.stringify({
          to: lastEmail?.fromEmail ?? meta.Para ?? "",
          subject: lastEmail ? `Re: ${lastEmail.subject}` : meta.Assunto ?? "",
          body: card.content,
          in_reply_to: lastEmail?.id ?? null,
        }),
      })
        .then(async () => {
          addVoxCard({ type: "confirmation", title: "Enviado com sucesso", content: `Resposta a ${lastEmail?.fromName ?? ""} enviada.` });
          await playTTS(`Email enviado com sucesso para ${lastEmail?.fromName ?? "o destinatário"}.`);
        })
        .catch(() => {
          addVoxCard({ type: "error", title: "Falha ao enviar", content: "O email não foi enviado. Tenta de novo.", actions: [{ label: "Tentar de novo", action: "send" }] });
          playTTS("O email não foi enviado. Tenta de novo.").catch(() => {});
        });
    }

    if (action === "edit" && card?.type === "draft") {
      const newText = window.prompt("Edita o draft:", card.content);
      if (newText !== null) updateVoxCard(cardId, { content: newText });
    }

    if (action === "redictate") {
      // Re-arm dictation mode from the last email context.
      const lastEmail = lastEmailRef.current;
      if (lastEmail) {
        pendingReplyRef.current = {
          emailId: lastEmail.id,
          fromName: lastEmail.fromName,
          fromEmail: lastEmail.fromEmail,
          subject: lastEmail.subject,
          body: lastEmail.body,
          armedAt: Date.now(),
        };
        addVoxCard({
          type: "transcription",
          title: "A ouvir de novo",
          content: "Toca no microfone e dita o novo rascunho.",
        });
        playTTS("Dita de novo.").catch(() => {});
      } else {
        addVoxCard({
          type: "error",
          title: "Sem contexto",
          content: "Perdi a referência ao email. Pede para responder novamente.",
        });
      }
    }

    if (action === "redo" || action === "retry") {
      recorder.reset();
      setMicState("idle");
    }

    if (action === "reauth") {
      // Clear any pending dictation — context is about to be invalidated by re-auth.
      pendingReplyRef.current = null;
      // Redirect to Google OAuth re-auth to get new scopes (calendar + contacts)
      if (typeof window !== "undefined") {
        window.location.href = `${process.env.NEXT_PUBLIC_API_URL ?? ""}/auth/google/start`;
      }
    }

    // -----------------------------------------------------------------------
    // Calendar CRUD confirmations — preview → Sim → execute
    // -----------------------------------------------------------------------
    const pendingId = card?.meta?.pendingId;
    const pending = pendingId ? pendingActionsRef.current.get(pendingId) : undefined;

    if (action === "calendar-cancel" && pendingId) {
      pendingActionsRef.current.delete(pendingId);
      addVoxCard({ type: "transcription", title: "Cancelado", content: "Ok, não fiz nada." });
      playTTS("Ok, cancelei.").catch(() => {});
    }

    if (action === "calendar-create-confirm" && pending?.type === "create") {
      const payload = pending.payload;
      // Detect if this was a reminder based on the confirm card meta shape
      // (meta.Lembrete is only set when is_reminder=true at the create branch).
      const wasReminder = Boolean(card?.meta?.Lembrete);
      pendingActionsRef.current.delete(pendingId!);
      createCalendarEvent(payload)
        .then(async (created) => {
          lastCalendarEventRef.current = {
            id: created.id,
            summary: created.summary,
            start: created.start,
            end: created.end,
            location: created.location || undefined,
          };
          addVoxCard({
            type: "calendar-create",
            title: wasReminder ? "Lembrete criado" : "Evento criado",
            content: wasReminder
              ? `Vou lembrar-te: "${created.summary}".`
              : `"${created.summary}" marcado.`,
            meta: {
              ...(wasReminder ? { Lembrete: created.summary } : { Título: created.summary }),
              Início: new Date(created.start).toLocaleString("pt-PT"),
              Fim: new Date(created.end).toLocaleString("pt-PT"),
            },
          });
          await playTTS(wasReminder ? "Fica combinado." : "Marcado.");
        })
        .catch(async (err) => {
          if (err instanceof ApiError && err.detail === "calendar_scope_missing") {
            addVoxCard({
              type: "error",
              title: "Permissão em falta",
              content: "Falta o scope do Calendar. Volta a autorizar.",
              actions: [{ label: "Autorizar agenda", action: "reauth" }],
            });
            await playTTS("Falta-me permissão para criar eventos.");
          } else {
            addVoxCard({ type: "error", title: "Erro", content: "Não consegui marcar. Tenta novamente." });
            await playTTS("Não consegui marcar.");
          }
        });
    }

    if (action === "calendar-edit-confirm" && pending?.type === "edit") {
      const { eventId, changes, summary } = pending;
      pendingActionsRef.current.delete(pendingId!);
      updateCalendarEvent(eventId, changes)
        .then(async (updated) => {
          lastCalendarEventRef.current = {
            id: updated.id,
            summary: updated.summary,
            start: updated.start,
            end: updated.end,
            location: updated.location || undefined,
          };
          addVoxCard({
            type: "calendar-create",
            title: "Evento alterado",
            content: `"${updated.summary}" atualizado.`,
            meta: {
              Título: updated.summary,
              Início: new Date(updated.start).toLocaleString("pt-PT"),
              Fim: new Date(updated.end).toLocaleString("pt-PT"),
            },
          });
          await playTTS("Alterado.");
        })
        .catch(async () => {
          addVoxCard({
            type: "error",
            title: "Erro",
            content: `Não consegui alterar "${summary}". Tenta novamente.`,
          });
          await playTTS("Não consegui alterar.");
        });
    }

    if (action === "calendar-delete-confirm" && pending?.type === "delete") {
      const { eventId, summary } = pending;
      pendingActionsRef.current.delete(pendingId!);
      deleteCalendarEvent(eventId)
        .then(async () => {
          // Clear context — the tracked event no longer exists.
          if (lastCalendarEventRef.current?.id === eventId) {
            lastCalendarEventRef.current = null;
          }
          addVoxCard({
            type: "confirmation",
            title: "Evento apagado",
            content: `"${summary}" foi removido da agenda.`,
          });
          await playTTS("Apagado.");
        })
        .catch(async () => {
          addVoxCard({
            type: "error",
            title: "Erro",
            content: `Não consegui apagar "${summary}". Tenta novamente.`,
          });
          await playTTS("Não consegui apagar.");
        });
    }

    if (action === "email-delete-confirm" && pending?.type === "email-trash") {
      const { emailId, fromName, subject } = pending;
      pendingActionsRef.current.delete(pendingId!);
      trashEmail(emailId)
        .then(async () => {
          // Clear lastEmailRef so a second "apaga esse email" doesn't
          // silently trash a stale reference.
          if (lastEmailRef.current?.id === emailId) {
            lastEmailRef.current = null;
          }
          addVoxCard({
            type: "confirmation",
            title: "Email apagado",
            content: `"${subject}" movido para o lixo.`,
            meta: { De: fromName, Assunto: subject },
          });
          await playTTS("Apagado.");
          // Refresh inbox list so the UI reflects the removal.
          qc.invalidateQueries({ queryKey: emailsKeys.list() });
        })
        .catch(async (err) => {
          const detail = err instanceof ApiError ? err.detail : "";
          const scopeMissing = detail === "gmail_modify_scope_missing";
          addVoxCard({
            type: "error",
            title: "Não consegui apagar",
            content: scopeMissing
              ? "Preciso de permissão para modificar emails. Volta a autorizar."
              : "Algo falhou. Tenta novamente.",
            ...(scopeMissing
              ? { actions: [{ label: "Autorizar", action: "reauth" }] }
              : {}),
          });
          await playTTS("Não consegui apagar.");
        });
    }
  }, [emailData?.emails, messages, addVoxCard, updateVoxCard, playTTS, setMicState, recorder, handleReadEmails, handleReplyToEmail, qc]);

  return (
    <div className="relative flex min-h-screen flex-col">
      <header
        className="glass-frost sticky top-0 z-10 px-5 pb-4"
        style={{ paddingTop: "max(2rem, calc(env(safe-area-inset-top) + 2rem))" }}
      >
        <div className="flex items-end justify-between">
          <div className="flex items-baseline gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[color:var(--primary)]/15 ring-1 ring-[color:var(--primary)]/25">
              <span className="hero-gradient-text font-[family-name:var(--font-display)] text-[22px] italic leading-none">
                V
              </span>
            </div>
            <div className="flex flex-col">
              <span className="font-[family-name:var(--font-display)] text-[30px] italic leading-none tracking-[-0.01em] text-[color:var(--text-primary)]">
                Vox
              </span>
              <span className="mt-1.5 text-[10px] uppercase tracking-[0.22em] text-[color:var(--text-tertiary)]">
                Secretário vocal
              </span>
            </div>
          </div>
          <button
            type="button"
            className="flex items-center gap-2 rounded-2xl bg-[color:var(--surface-elevated)]/70 px-3.5 py-2 text-xs font-medium text-[color:var(--text-secondary)] ring-1 ring-[color:var(--hairline)] backdrop-blur transition-colors hover:text-[color:var(--text-primary)]"
            aria-label="Selecionar conta"
          >
            <span className="h-2 w-2 rounded-full bg-[color:var(--primary)]" />
            <span>Pessoal</span>
            <ChevronDown className="h-3 w-3" />
          </button>
        </div>
      </header>

      <div
        ref={scrollRef}
        className="flex-1 space-y-5 overflow-y-auto px-5 py-5"
        style={{ paddingBottom: "8rem" }}
      >
        {messages.map((msg) => {
          if (msg.role === "vox") {
            return <VoxCardComponent key={msg.id} card={msg} onAction={handleCardAction} />;
          }

          return (
            <div key={msg.id} className="flex flex-col items-end animate-fade-in-up">
              <div className="max-w-[80%] rounded-3xl rounded-br-lg bg-[color:var(--primary)]/12 px-5 py-3 ring-1 ring-[color:var(--primary)]/20 backdrop-blur">
                {msg.isVoice ? (
                  <p className="font-[family-name:var(--font-mono)] text-[13px] leading-relaxed text-[color:var(--text-primary)]">
                    {msg.text}
                  </p>
                ) : (
                  <p className="text-sm leading-relaxed text-[color:var(--text-primary)]">
                    {msg.text}
                  </p>
                )}
              </div>
              {msg.isVoice ? (
                <span className="mr-2 mt-1 flex items-center gap-1 text-[10px] text-[color:var(--text-tertiary)]">
                  <Mic
                    className="h-2.5 w-2.5 text-[color:var(--voice)]"
                    strokeWidth={2}
                    aria-label="Transcrito da voz"
                  />
                  <span title="Transcrito da voz">
                    {new Date(msg.createdAt).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </span>
              ) : (
                <span className="mr-2 mt-1 text-[10px] text-[color:var(--text-tertiary)]">
                  {new Date(msg.createdAt).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}
                </span>
              )}
            </div>
          );
        })}

        {(micState === "listening" || micState === "silence-detected") && (
          <div className="flex flex-col items-end animate-fade-in-up">
            <div
              className={cn(
                "max-w-[80%] rounded-3xl rounded-br-lg px-5 py-3 ring-1 backdrop-blur",
                micState === "listening"
                  ? "bg-[color:var(--voice)]/10 ring-[color:var(--voice)]/22"
                  : "bg-[color:var(--primary)]/10 ring-[color:var(--primary)]/20",
              )}
            >
              <div className="flex items-center gap-2">
                {micState === "listening" && (
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[color:var(--voice)] opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-[color:var(--voice)]" />
                  </span>
                )}
                <span
                  className={cn(
                    "text-sm",
                    micState === "listening"
                      ? "text-[color:var(--voice)]"
                      : "text-[color:var(--text-secondary)]",
                  )}
                >
                  {micState === "listening" ? "A ouvir…" : "A processar…"}
                </span>
              </div>
            </div>
          </div>
        )}

        {messages.length === 0 && (
          <div className="flex flex-1 flex-col items-center justify-center px-6 py-24 text-center">
            <p className="max-w-[300px] font-[family-name:var(--font-display)] text-[34px] italic leading-[1.12] tracking-[-0.01em] text-[color:var(--text-primary)]">
              O que queres fazer hoje?
            </p>
            <p className="mt-5 max-w-[260px] text-sm leading-relaxed text-[color:var(--text-secondary)]">
              Toca no microfone e fala comigo como falarias com um secretário.
            </p>
          </div>
        )}
      </div>

      <div
        className="glass-frost fixed inset-x-0 bottom-24 z-40 mx-4 rounded-[28px] border-[color:var(--hairline)]"
        style={{ paddingBottom: "0.5rem" }}
      >
        <div className="flex flex-col items-center gap-1.5 px-5 py-3">
          {micState === "listening" && (
            <span className="text-[11px] font-medium text-[color:var(--voice)]/80">
              A gravar — toca para parar ou aguarda silêncio
            </span>
          )}
          {micState === "silence-detected" && (
            <span className="text-[11px] font-medium text-[color:var(--text-tertiary)]">
              Silêncio detectado — a processar…
            </span>
          )}
          <MicButton state={micState} onClick={handleMicClick} />
        </div>
      </div>
    </div>
  );
}
