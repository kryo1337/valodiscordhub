import { Link } from "react-router-dom";
import { Users, Swords, Trophy, ArrowRight, Zap, Shield, Target } from "lucide-react";
import { Button } from "@/components/ui";
import { useAuth } from "@/hooks";

export default function Home() {
  const { isAuthenticated } = useAuth();

  const features = [
    {
      icon: Users,
      title: "Queue System",
      description: "Join queues for your rank group and get matched with players of similar skill.",
    },
    {
      icon: Swords,
      title: "Custom Matches",
      description: "Balanced team compositions with captain picks and map selection.",
    },
    {
      icon: Trophy,
      title: "Leaderboards",
      description: "Compete for the top spots and track your progress over time.",
    },
    {
      icon: Target,
      title: "Fair Play",
      description: "ELO-based matchmaking ensures competitive and balanced games.",
    },
    {
      icon: Shield,
      title: "Discord Integration",
      description: "Seamlessly works with Discord for team communication and coordination.",
    },
    {
      icon: Zap,
      title: "Real-time Updates",
      description: "Live updates keep you informed about queue status and match progress.",
    },
  ];

  return (
    <div className="space-y-20">
      <section className="relative py-20 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-valorant-red/10 via-transparent to-valorant-cyan/5 pointer-events-none" />
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-valorant-red/50 to-transparent" />

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="mb-8">
            <h1 className="text-6xl md:text-8xl font-black tracking-tighter">
              <span className="text-valorant-red">VALO</span>
              <span className="text-valorant-light">HUB</span>
            </h1>
            <div className="h-1 w-32 bg-valorant-red mx-auto mt-6" />
          </div>

          <p className="text-xl text-valorant-gray mb-10 max-w-2xl mx-auto leading-relaxed">
            Competitive custom matches for the Valorant community.
            <br className="hidden sm:block" />
            Queue up. Get matched. Dominate.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {isAuthenticated ? (
              <>
                <Link to="/queue">
                  <Button size="lg">
                    <Users className="h-5 w-5 skew-x-[3deg]" />
                    Join Queue
                  </Button>
                </Link>
                <Link to="/leaderboard">
                  <Button variant="outline" size="lg">
                    <Trophy className="h-5 w-5 skew-x-[3deg]" />
                    Leaderboard
                  </Button>
                </Link>
              </>
            ) : (
              <Link to="/login">
                <Button size="lg">
                  Get Started
                  <ArrowRight className="h-5 w-5 skew-x-[3deg]" />
                </Button>
              </Link>
            )}
          </div>
        </div>
      </section>

      <section>
        <div className="flex items-center gap-4 mb-12">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent to-valorant-gray/20" />
          <h2 className="text-sm uppercase tracking-[0.3em] text-valorant-gray font-bold">
            Why ValoHub
          </h2>
          <div className="h-px flex-1 bg-gradient-to-l from-transparent to-valorant-gray/20" />
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-px bg-valorant-gray/10">
          {features.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="group bg-valorant-darker p-8 hover:bg-valorant-dark transition-colors duration-300"
            >
              <div className="flex items-start gap-4">
                <div className="p-3 bg-valorant-red/10 border-l-2 border-valorant-red group-hover:bg-valorant-red/20 transition-colors">
                  <Icon className="h-5 w-5 text-valorant-red" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-valorant-light uppercase tracking-wider mb-2">
                    {title}
                  </h3>
                  <p className="text-sm text-valorant-gray leading-relaxed">
                    {description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {!isAuthenticated && (
        <section className="relative">
          <div className="absolute inset-0 bg-valorant-red/5 border-l-2 border-valorant-red" />
          <div className="relative py-16 px-8 text-center">
            <h2 className="text-3xl font-black uppercase tracking-tight mb-4">
              Ready to compete?
            </h2>
            <p className="text-valorant-gray mb-8 max-w-md mx-auto">
              Join thousands of players in competitive custom matches.
            </p>
            <Link to="/login">
              <Button size="lg">
                Login with Discord
                <ArrowRight className="h-5 w-5 skew-x-[3deg]" />
              </Button>
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
