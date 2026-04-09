import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Link from 'next/link';
import { Bot, Library, ScrollText } from 'lucide-react';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'LexAgent | EU AI Act Compliance Assistant',
  description: 'AI-powered compliance and classification for the EU AI Act.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <style dangerouslySetInnerHTML={{__html: `
          :root {
            --background: 220 20% 97%;
            --foreground: 222.2 47.4% 11.2%;
            --primary: 221.2 83.2% 53.3%;
            --primary-foreground: 210 40% 98%;
          }
          .dark {
            --background: 224 71% 4%;
            --foreground: 213 31% 91%;
            --primary: 210 40% 98%;
            --primary-foreground: 222.2 47.4% 1.2%;
          }
          body {
            background-color: hsl(var(--background));
            color: hsl(var(--foreground));
          }
        `}} />
      </head>
      <body className={`${inter.className} min-h-screen flex`}>
        {/* Sidebar */}
        <aside className="w-64 border-r border-white/10 bg-black/20 p-4 flex flex-col gap-6">
          <div className="flex items-center gap-2 px-2 text-xl font-semibold tracking-tight text-white mb-4">
            <span className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Bot className="w-5 h-5 text-white" />
            </span>
            LexAgent
          </div>
          <nav className="flex flex-col gap-2">
            <Link href="/chat" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-white/10 transition-colors text-sm text-gray-300 hover:text-white">
              <Bot className="w-4 h-4" /> Agent Chat
            </Link>
            <Link href="/inventory" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-white/10 transition-colors text-sm text-gray-300 hover:text-white">
              <Library className="w-4 h-4" /> AI Inventory
            </Link>
            <Link href="/audit" className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-white/10 transition-colors text-sm text-gray-300 hover:text-white">
              <ScrollText className="w-4 h-4" /> Audit Log
            </Link>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col h-screen overflow-hidden">
          {children}
        </main>
      </body>
    </html>
  );
}
