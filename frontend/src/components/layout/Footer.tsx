import { Github, MessageCircle } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t-2 border-valorant-gray/10 bg-valorant-darker">
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="h-7 w-7 bg-valorant-red flex items-center justify-center skew-x-[-6deg]">
              <span className="text-white font-black text-sm skew-x-[6deg]">V</span>
            </div>
            <span className="text-sm text-valorant-gray">
              ValoHub <span className="text-valorant-gray/50">2025</span>
            </span>
          </div>

          <div className="flex items-center gap-1">
            <a
              href="https://discord.gg/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 text-valorant-gray hover:text-valorant-light hover:bg-valorant-gray/10 transition-colors text-xs uppercase tracking-wider font-bold"
              aria-label="Join our Discord"
            >
              <MessageCircle className="h-4 w-4" />
              Discord
            </a>
            <a
              href="https://github.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 text-valorant-gray hover:text-valorant-light hover:bg-valorant-gray/10 transition-colors text-xs uppercase tracking-wider font-bold"
              aria-label="View on GitHub"
            >
              <Github className="h-4 w-4" />
              GitHub
            </a>
          </div>

          <p className="text-[10px] text-valorant-gray/30 uppercase tracking-widest">
            Not affiliated with Riot Games
          </p>
        </div>
      </div>
    </footer>
  );
}
