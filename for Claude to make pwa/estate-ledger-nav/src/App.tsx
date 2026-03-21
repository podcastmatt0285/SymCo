import { SideNav } from './components/SideNav';

export default function App() {
  return (
    <div className="flex h-screen w-full bg-[#0a0502]">
      <SideNav />
      <main className="flex-1 flex flex-col relative overflow-hidden">
        {/* Background Texture */}
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none" 
             style={{ backgroundImage: 'url("https://www.transparenttextures.com/patterns/dark-leather.png")' }} />
        
        <div className="flex-1 flex items-center justify-center p-12 relative z-10 text-center">
          <div className="text-radio-accent/5 font-display text-[10vw] font-black uppercase tracking-tighter select-none italic leading-none">
            Estate <br /> Management
          </div>
        </div>

        {/* Bottom Status Bar */}
        <div className="h-10 bg-radio-panel border-t border-radio-accent/20 flex items-center px-8 justify-between">
          <div className="flex items-center gap-6">
            <span className="text-[9px] font-bold text-radio-accent uppercase tracking-widest opacity-40">Status: Ledger Synchronized</span>
            <span className="text-[9px] font-bold text-radio-accent uppercase tracking-widest opacity-40">Market: Open</span>
          </div>
          <div className="text-[9px] font-bold text-radio-accent uppercase tracking-widest opacity-40">
            Wadsworth Carter Estate
          </div>
        </div>
      </main>
    </div>
  );
}
