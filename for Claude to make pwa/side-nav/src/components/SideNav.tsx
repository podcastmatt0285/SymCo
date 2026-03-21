import React from 'react';
import { 
  Map, 
  LayoutGrid, 
  Building2, 
  MapPin, 
  Coins, 
  Pickaxe, 
  Wallet, 
  ShoppingBag, 
  Store,
  ChevronDown,
  ChevronRight,
  Settings,
  User,
  TrendingUp
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface NavNode {
  label: string;
  icon: React.ReactNode;
  children?: NavNode[];
}

const navData: NavNode[] = [
  {
    label: 'Land',
    icon: <Map size={20} />,
    children: [
      { label: 'Land Market', icon: <ShoppingBag size={18} /> },
      {
        label: 'Districts',
        icon: <LayoutGrid size={18} />,
        children: [
          { label: 'Districts Market', icon: <Store size={16} /> },
          {
            label: 'Cities',
            icon: <Building2 size={16} />,
            children: [
              {
                label: 'Counties',
                icon: <MapPin size={14} />,
                children: [
                  {
                    label: 'Crypto Exchange',
                    icon: <Coins size={14} />,
                    children: [
                      {
                        label: 'Mining',
                        icon: <Pickaxe size={12} />,
                        children: [
                          { label: 'Wallet', icon: <Wallet size={12} /> }
                        ]
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
];

interface NavItemProps {
  node: NavNode;
  level: number;
  activeTab: string;
  setActiveTab: (val: string) => void;
}

const NavItem: React.FC<NavItemProps> = ({ node, level, activeTab, setActiveTab }) => {
  // Keep Land and Districts open by default to show the nesting
  const [isOpen, setIsOpen] = React.useState(level < 2);
  const hasChildren = node.children && node.children.length > 0;
  const isActive = activeTab === node.label;

  return (
    <div className="w-full">
      <motion.button
        whileHover={{ x: 4 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => {
          setActiveTab(node.label);
          if (hasChildren) setIsOpen(!isOpen);
        }}
        className={`w-full flex items-center gap-3 px-6 py-2.5 transition-all duration-300 group border-b border-radio-accent/5 ${
          isActive 
            ? 'bg-radio-accent/10 text-white' 
            : 'text-radio-text/50 hover:text-radio-text hover:bg-radio-accent/5'
        }`}
        style={{ paddingLeft: `${level * 16 + 24}px` }}
      >
        <span className={`${isActive ? 'text-radio-accent' : 'group-hover:text-radio-accent'} transition-colors`}>
          {node.icon}
        </span>
        <span className={`font-display italic uppercase tracking-widest text-left flex-1 ${level === 0 ? 'text-base' : 'text-xs'}`}>
          {node.label}
        </span>
        {hasChildren && (
          <span className="text-radio-accent/30 group-hover:text-radio-accent transition-colors">
            {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </span>
        )}
        {isActive && !hasChildren && (
          <div className="w-1 h-1 rounded-full bg-radio-accent shadow-[0_0_8px_#B08D57]" />
        )}
      </motion.button>
      
      <AnimatePresence>
        {hasChildren && isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden bg-black/10"
          >
            {node.children!.map((child) => (
              <NavItem 
                key={child.label} 
                node={child} 
                level={level + 1} 
                activeTab={activeTab} 
                setActiveTab={setActiveTab} 
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export const SideNav = () => {
  const [activeTab, setActiveTab] = React.useState('Land');

  return (
    <nav className="w-80 h-screen radio-box flex flex-col relative z-10 radio-glow">
      <div className="radio-inlay" />
      
      {/* Header */}
      <div className="p-8 border-b border-radio-accent/30 bg-radio-panel text-center relative">
        <div className="flex items-center justify-center gap-3 mb-2">
          <Map className="text-radio-accent" size={20} />
          <h1 className="font-display text-2xl font-black uppercase tracking-[0.1em] radio-accent-text">
            ESTATE<span className="text-white/20">.</span>MGR
          </h1>
        </div>
        <p className="text-[9px] italic uppercase tracking-[0.3em] opacity-40">
          Wadsworth Land Dashboard
        </p>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto no-scrollbar py-2">
        <div className="mb-4">
          {navData.map((node) => (
            <NavItem 
              key={node.label} 
              node={node} 
              level={0} 
              activeTab={activeTab} 
              setActiveTab={setActiveTab} 
            />
          ))}
        </div>

        {/* Decorative Flower SVG from Source */}
        <div className="mt-8 flex justify-center opacity-5 pointer-events-none">
          <svg className="w-24 h-24 rose-sway" viewBox="0 0 201.5 207.54" xmlns="http://www.w3.org/2000/svg">
            <g transform="matrix(.15791 0 0 .15791 16.376 41.416)">
              <path fill="#2D5A27" d="m470.03 168.72c-34.81 0.55-75.98 25.14-120.23 80.45 287.24-187.49 318.09 308.34-234.97 802.83h105.53c11.37-10.2 22.06-19.9 30.58-28.8 404.11-366.71 376.62-856.94 219.09-854.48z"/>
              <path fill="#B08D57" d="m357.14 205.1c0.02 71.81-65.23 130.02-145.71 130.02-80.49 0-145.73-58.21-145.72-130.02-0.009-71.81 65.23-130.02 145.72-130.02 80.48-0.002 145.73 58.21 145.71 130.02z" transform="translate(219.15 -163.07)"/>
            </g>
          </svg>
        </div>
      </div>

      {/* Wallet Widget in Nav */}
      <div className="p-6 bg-radio-panel border-t border-radio-accent/30 relative">
        <div className="flex items-center justify-between mb-4">
          <div className="flex flex-col">
            <span className="text-[8px] uppercase tracking-widest text-radio-accent font-bold">Total Assets</span>
            <span className="text-lg italic uppercase text-white font-black tracking-tighter">$1,240,500</span>
          </div>
          <div className="w-10 h-10 rounded-full border border-radio-accent/30 flex items-center justify-center text-radio-accent bg-black/40">
            <TrendingUp size={18} />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex-1 h-1 bg-black rounded-full overflow-hidden border border-radio-accent/10">
            <div className="w-[65%] h-full bg-gradient-to-r from-radio-accent/50 to-radio-accent" />
          </div>
          <span className="text-[10px] font-bold text-radio-accent opacity-60">+4.2%</span>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 bg-radio-bg border-t border-radio-accent/10 flex gap-2">
        <button className="flex-1 flex items-center justify-center gap-2 py-2 text-radio-accent/40 hover:text-radio-accent transition-colors group border border-radio-accent/10 hover:border-radio-accent/30">
          <Settings size={14} />
          <span className="text-[10px] uppercase tracking-widest font-bold">Config</span>
        </button>
        <button className="flex-1 flex items-center justify-center gap-2 py-2 text-radio-accent/40 hover:text-radio-accent transition-colors group border border-radio-accent/10 hover:border-radio-accent/30">
          <User size={14} />
          <span className="text-[10px] uppercase tracking-widest font-bold">Profile</span>
        </button>
      </div>
    </nav>
  );
};
