import { AuthTokenCapture } from "@/components/auth-token-capture";
import { BottomNavbar } from "@/components/bottom-navbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col">
      <AuthTokenCapture />
      <div className="aurora-bloom" aria-hidden />
      <main className="relative z-10 flex-1 pb-24">{children}</main>
      <BottomNavbar />
    </div>
  );
}
