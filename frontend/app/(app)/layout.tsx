import { AuthTokenCapture } from "@/components/auth-token-capture";
import { BottomNavbar } from "@/components/bottom-navbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <AuthTokenCapture />
      <main className="flex-1 pb-16">{children}</main>
      <BottomNavbar />
    </div>
  );
}
