import "./globals.css";

export const metadata = {
  title: "Mapping UI",
  description: "Mapping validation dashboard",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <header className="border-b bg-white">
          <div className="container py-4 flex items-center justify-between">
            <div className="text-lg font-semibold">ERP Mapping Platform</div>
            <nav className="text-sm text-slate-600 flex gap-4">
              <a className="hover:text-slate-900" href="/mapping">Mapping</a>
              <a className="hover:text-slate-900" href="/">Home</a>
            </nav>
          </div>
        </header>

        <main className="container py-8">{children}</main>
      </body>
    </html>
  );
}
