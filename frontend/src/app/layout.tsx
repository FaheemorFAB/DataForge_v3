import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DataForge",
  description: "AI-powered Data Analytics Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      data-theme="dark"
      data-font="inter"
      data-scroll-behavior="smooth"
    >
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <script
          id="theme-init"
          async
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('analyst-theme')||'light';document.documentElement.setAttribute('data-theme',t);var dark=['dark','dracula','slate','emerald','nord','luxury'];if(dark.indexOf(t)!==-1){document.documentElement.classList.add('dark')}else{document.documentElement.classList.remove('dark')}var f=localStorage.getItem('analyst-font')||'inter';document.documentElement.setAttribute('data-font',f)}catch(e){}})()`,
          }}
        />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Outfit:wght@300;400;500;600;700;800;900&family=Poppins:wght@300;400;500;600;700;800;900&family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=Rajdhani:wght@300;400;500;600;700&family=Roboto+Mono:ital,wght@0,100..700;1,100..700&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
