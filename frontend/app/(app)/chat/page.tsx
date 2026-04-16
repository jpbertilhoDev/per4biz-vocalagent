"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";

import { useChatStore, type VoxCard, type MicState } from "@/lib/chat-store";
import { VoxCard as VoxCardComponent } from "@/components/vox-card";
import { MicButton } from "@/components/mic-button";
import { useMediaRecorder } from "@/lib/use-media-recorder";
import {
  postTranscribe,
  postPolish,
  postIntent,
  fetchTTS,
  speakFallback,
  type PolishContext,
} from "@/lib/voice-api";
import {
  emailsKeys,
  listEmails,
  getEmail,
  listCalendarEvents,
  createCalendarEvent,
  searchContacts,
  type EmailListResponse,
  type EmailDetail,
} from "@/lib/queries";
import { apiFetch } from "@/lib/api";
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
  const scrollRef = useRef<HTMLDivElement>(null);
  const [welcomeSent, setWelcomeSent] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const lastEmailRef = useRef<{ fromName: string; fromEmail: string; subject: string; body: string; id: string } | null>(null);

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

  const playTTS = useCallback(async (text: string): Promise<void> => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ""; }
    if (audioUrlRef.current) { URL.revokeObjectURL(audioUrlRef.current); audioUrlRef.current = null; }

    setMicState("speaking");
    try {
      const blob = await fetchTTS(text.slice(0, 4000));
      if (blob.size < 100) {
        throw new Error(`TTS returned suspiciously small audio: ${blob.size} bytes`);
      }
      const url = URL.createObjectURL(blob);
      audioUrlRef.current = url;
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        setMicState("idle");
        URL.revokeObjectURL(url);
        audioUrlRef.current = null;
      };
      audio.onerror = () => {
        console.warn("[Vox] Audio playback error, falling back to browser TTS");
        setMicState("idle");
        URL.revokeObjectURL(url);
        audioUrlRef.current = null;
        speakFallback(text.slice(0, 4000)).catch(() => {});
      };
      await audio.play();
    } catch (err) {
      console.warn("[Vox] ElevenLabs TTS failed, trying browser fallback:", err);
      // ElevenLabs failed — try browser TTS fallback
      try {
        await speakFallback(text.slice(0, 4000));
      } catch {
        // Both TTS methods failed — show feedback
        addVoxCard({
          type: "error",
          title: "Voz indisponível",
          content: "Não foi possível reproduzir áudio. Verifica a tua ligação.",
        });
      }
      setMicState("idle");
    }
  }, [setMicState, addVoxCard]);

  const handleReadEmails = useCallback(async (count = 3) => {
    if (!emailData?.emails?.length) {
      addVoxCard({ type: "error", title: "Sem emails", content: "Não encontrei emails na caixa de entrada." });
      return;
    }

    const toRead = emailData.emails.slice(0, count);
    const summaryParts: string[] = [];

    for (const email of toRead) {
      addVoxCard({
        type: "email-read",
        title: email.subject || "(sem assunto)",
        content: email.snippet || "(sem conteúdo)",
        meta: {
          De: email.from_name ?? email.from_email,
          Hora: new Date(email.received_at).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" }),
        },
        actions: [
          { label: "Ouvir", action: "tts" },
          { label: "Ouvir completo", action: "tts-full" },
          { label: "Responder", action: "reply" },
        ],
      });

      summaryParts.push(`${email.from_name ?? email.from_email}: ${email.subject}. ${email.snippet?.slice(0, 80) ?? ""}`);
    }

    const ttsText = `Tens ${toRead.length} email${toRead.length > 1 ? "s" : ""}. ${summaryParts.join(". ")}`;
    await playTTS(ttsText);
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

      addVoxCard({
        type: "transcription",
        title: `Responder a ${detail.from_name ?? detail.from_email}`,
        content: `Assunto: ${detail.subject}. Toca no microfone para ditar a tua resposta.`,
        meta: { De: detail.from_name ?? detail.from_email, Assunto: detail.subject },
      });

      await playTTS(`Vais responder a ${detail.from_name ?? detail.from_email} sobre ${detail.subject}. Dita a tua resposta.`);
    } catch {
      addVoxCard({ type: "error", title: "Erro", content: "Não consegui carregar o email para responder." });
    }
  }, [addVoxCard, playTTS]);

  const processIntent = useCallback(async (transcript: string) => {
    let intentResult: { intent: string; params: Record<string, unknown> };

    try {
      const result = await postIntent(transcript);
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
          const voiceSummary = events.slice(0, 5).map((e) => `${e.summary} ${e.is_all_day ? "todo o dia" : `às ${new Date(e.start).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}`}`).join(". ");
          await playTTS(`Tens ${events.length} evento${events.length > 1 ? "s" : ""}. ${voiceSummary}`);
        }
      } catch {
        addVoxCard({ type: "error", title: "Erro", content: "Não consegui carregar a agenda." });
        await playTTS("Não consegui carregar a agenda.");
      }
    } else if (intent === "calendar_create") {
      const { summary, start, end } = intentResult.params as { summary?: string; start?: string; end?: string };
      if (!summary) {
        addVoxCard({ type: "transcription", title: "Criar evento", content: "Qual é o título do evento que queres criar?" });
        await playTTS("Qual é o título do evento que queres criar?");
        return;
      }
      try {
        const now = new Date();
        const defaultStart = start ?? new Date(now.getTime() + 3600000).toISOString();
        const defaultEnd = end ?? new Date(now.getTime() + 7200000).toISOString();
        const created = await createCalendarEvent({ summary, start: defaultStart, end: defaultEnd });
        addVoxCard({
          type: "calendar-create",
          title: "Evento criado",
          content: `"${created.summary}" criado com sucesso.`,
          meta: {
            Título: created.summary,
            Início: new Date(created.start).toLocaleString("pt-PT"),
            Fim: new Date(created.end).toLocaleString("pt-PT"),
          },
        });
        await playTTS(`Evento "${created.summary}" criado com sucesso.`);
      } catch {
        addVoxCard({ type: "error", title: "Erro", content: "Não consegui criar o evento." });
        await playTTS("Não consegui criar o evento.");
      }
    } else if (intent === "calendar_edit") {
      addVoxCard({ type: "transcription", title: "Editar evento", content: "Para editar um evento, abre a tab Agenda e faz as alterações lá." });
      await playTTS("Para editar um evento, abre a aba Agenda e faz as alterações lá.");
    } else if (intent === "calendar_delete") {
      addVoxCard({ type: "transcription", title: "Apagar evento", content: "Para apagar um evento, abre a tab Agenda e remove-o lá." });
      await playTTS("Para apagar um evento, abre a aba Agenda e remove-o lá.");
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
      } catch {
        addVoxCard({ type: "error", title: "Erro", content: "Não consegui procurar contactos." });
        await playTTS("Não consegui procurar contactos.");
      }
    } else {
      addVoxCard({
        type: "transcription",
        title: "Não entendi",
        content: `Quiseste dizer "${transcript}"? Experimenta dizer: "lê os meus emails", "responde ao último email", "agenda" ou "procura contacto".`,
      });
      await playTTS("Não percebi o que queres. Experimenta dizer lê os meus emails, agenda, ou procura contacto.");
    }
  }, [emailData?.emails, messages, addVoxCard, handleReadEmails, handleReplyToEmail, playTTS]);

  const handleMicClick = useCallback(() => {
    if (micState === "idle") {
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

    addVoxCard({ type: "transcription", title: "A processar…", content: "" });

    let transcribedText = "";

    postTranscribe(recorder.audioBlob)
      .then((result) => {
        transcribedText = result.text;
        addUserMessage(transcribedText, true);
        return processIntent(transcribedText);
      })
      .catch(() => {
        addVoxCard({ type: "error", title: "Erro ao processar", content: "Não foi possível processar a gravação. Tenta de novo.", actions: [{ label: "Tentar de novo", action: "retry" }] });
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
      playTTS(`${card.title}. ${card.content}`);
    }

    if (action === "tts-full" && card?.meta?.De) {
      const email = emailData?.emails?.find((e) => (e.from_name ?? e.from_email) === card.meta!.De);
      if (email) {
        getEmail(email.id).then((detail: EmailDetail) => {
          lastEmailRef.current = {
            fromName: detail.from_name ?? detail.from_email,
            fromEmail: detail.from_email,
            subject: detail.subject,
            body: detail.body_text,
            id: detail.id,
          };
          playTTS(`Email de ${detail.from_name ?? detail.from_email}. Assunto: ${detail.subject}. ${detail.body_text.slice(0, 2000)}`);
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

    if (action === "redo" || action === "retry") {
      recorder.reset();
      setMicState("idle");
    }
  }, [emailData?.emails, messages, addVoxCard, updateVoxCard, playTTS, setMicState, recorder, handleReadEmails, handleReplyToEmail]);

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header
        className="glass-frost sticky top-0 z-10 px-5 py-4"
        style={{ paddingTop: "max(1rem, env(safe-area-inset-top))" }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/20 ring-1 ring-primary/30">
              <span className="hero-gradient-text text-sm font-bold">V</span>
            </div>
            <div>
              <h1 className="text-base font-semibold text-text-primary leading-none">Vox</h1>
              <span className="text-[10px] text-text-tertiary">Agente vocal</span>
            </div>
          </div>
          <button
            type="button"
            className="flex items-center gap-2 rounded-2xl bg-surface-elevated px-4 py-2 text-xs font-medium text-text-secondary ring-1 ring-divider transition-colors hover:text-text-primary"
            aria-label="Selecionar conta"
          >
            <span className="h-2 w-2 rounded-full bg-primary" />
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
              <div className="max-w-[80%] rounded-3xl rounded-br-lg bg-primary/12 px-5 py-3 ring-1 ring-primary/20">
                {msg.isVoice ? (
                  <p className="font-mono text-sm leading-relaxed text-text-primary">{msg.text}</p>
                ) : (
                  <p className="text-sm leading-relaxed text-text-primary">{msg.text}</p>
                )}
              </div>
              <span className="mr-2 mt-1 text-[10px] text-text-tertiary">
                {new Date(msg.createdAt).toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          );
        })}

        {(micState === "listening" || micState === "silence-detected") && (
          <div className="flex flex-col items-end animate-fade-in-up">
            <div className={cn(
              "max-w-[80%] rounded-3xl rounded-br-lg px-5 py-3 ring-1",
              micState === "listening"
                ? "bg-voice/8 ring-voice/20"
                : "bg-primary/8 ring-primary/20",
            )}>
              <div className="flex items-center gap-2">
                {micState === "listening" && (
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-voice opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-voice" />
                  </span>
                )}
                <span className={cn("text-sm", micState === "listening" ? "text-voice" : "text-text-secondary")}>
                  {micState === "listening" ? "A ouvir…" : "A processar…"}
                </span>
              </div>
            </div>
          </div>
        )}

        {messages.length === 0 && (
          <div className="flex flex-1 flex-col items-center justify-center py-24 text-center">
            <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20">
              <span className="hero-gradient-text text-3xl font-bold">V</span>
            </div>
            <p className="mb-2 text-base font-semibold text-text-primary">Olá! Sou o Vox.</p>
            <p className="max-w-[240px] text-sm leading-relaxed text-text-tertiary">
              Toca no microfone para falares comigo. Eu leio, respondo e organizo os teus emails.
            </p>
          </div>
        )}
      </div>

      <div
        className="glass-frost fixed right-0 bottom-16 left-0 z-40 border-t border-divider/50"
        style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
      >
        <div className="flex flex-col items-center gap-1.5 px-5 py-3">
          {micState === "listening" && (
            <span className="text-[11px] font-medium text-voice/80">
              A gravar — toca para parar ou aguarda silêncio
            </span>
          )}
          {micState === "silence-detected" && (
            <span className="text-[11px] font-medium text-text-tertiary">
              Silêncio detectado — a processar…
            </span>
          )}
          <MicButton state={micState} onClick={handleMicClick} />
        </div>
      </div>
    </div>
  );
}
