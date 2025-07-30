export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col h-full relative">
      <div className="md:hidden w-screen absolute -top-6 left-0 h-6 z-10 bg-gradient-to-b from-background/40 to-transparent shadow-[0_7px_16px_-1px_rgba(0,0,0,0.4)]" />
      {children}
    </div>
  );
}
