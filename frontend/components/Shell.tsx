import Link from "next/link";
import { Building2, BarChart3, Calculator, Gauge, Scale, Search, TrendingUp } from "lucide-react";

const nav = [
  ["/", "Landing", Building2], ["/dashboard", "Dashboard", BarChart3], ["/predictor", "Predictor", Calculator],
  ["/value-checker", "Value Checker", Gauge], ["/compare", "Compare", Scale], ["/explorer", "Explorer", Search],
  ["/recommendations", "Investments", TrendingUp], ["/performance", "Performance", BarChart3]
];

export function Shell({ children }: { children: React.ReactNode }) {
  return <main className="min-h-screen">
    <aside className="fixed left-4 top-4 bottom-4 hidden w-64 rounded-3xl glass p-4 shadow-xl lg:block">
      <div className="mb-8 flex items-center gap-3"><div className="rounded-2xl bg-teal-600 p-3 text-white"><Building2 /></div><div><h2 className="font-black">Islamabad Property</h2><p className="text-xs text-slate-500">Price Intelligence</p></div></div>
      <nav className="space-y-2">{nav.map(([href,label,Icon]:any)=><Link key={href} href={href} className="flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-bold text-slate-700 hover:bg-teal-50 hover:text-teal-700"><Icon size={18}/>{label}</Link>)}</nav>
    </aside>
    <div className="mx-auto max-w-7xl px-4 py-6 lg:ml-72">
      <div className="mb-4 flex flex-wrap gap-2 lg:hidden">{nav.map(([href,label]:any)=><Link key={href} href={href} className="rounded-full bg-white px-3 py-2 text-xs font-bold shadow">{label}</Link>)}</div>
      {children}
    </div>
  </main>;
}

export function Card({ children, className="" }: { children: React.ReactNode; className?: string }) { return <div className={`glass rounded-3xl p-6 shadow-xl ${className}`}>{children}</div>; }
export function StatCard({ label, value }: { label: string; value: any }) { return <Card><p className="text-sm font-bold text-slate-500">{label}</p><h3 className="mt-2 text-3xl font-black">{value}</h3></Card>; }
