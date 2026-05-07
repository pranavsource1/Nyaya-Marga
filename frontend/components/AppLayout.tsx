'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, Upload, Search, CheckCircle,
  ShieldCheck, ScrollText, FileBarChart, Users,
  ChevronRight, LogOut,
} from 'lucide-react';
import { GovRibbon } from './GovRibbon';

interface AppLayoutProps { children: React.ReactNode; }

const NAV_SECTIONS = [
  {
    heading: 'Operations',
    items: [
      { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { href: '/', label: 'Upload Judgments', icon: Upload, exact: true },
      { href: '/cases', label: 'All Cases', icon: FileBarChart },
    ],
  },
  {
    heading: 'Verification',
    items: [
      { href: '/verify', label: 'Verification Queue', icon: CheckCircle },
    ],
  },
  {
    heading: 'Research',
    items: [
      { href: '/search', label: 'Precedent Search', icon: Search },
    ],
  },
  {
    heading: 'Compliance',
    items: [
      { href: '/audit', label: 'Audit Trail', icon: ScrollText },
      { href: '/users', label: 'Users & Roles', icon: Users },
    ],
  },
];

export function AppLayout({ children }: AppLayoutProps) {
  const pathname = usePathname();
  const isActive = (path: string, exact?: boolean) => {
    if (exact) return pathname === path;
    return pathname === path || pathname.startsWith(`${path}/`);
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden font-sans bg-slate-50">
      <GovRibbon />
      <div className="flex flex-1 overflow-hidden">
        {/* SIDEBAR */}
        <aside className="w-[260px] shrink-0 flex flex-col bg-gov-900 text-white z-20 border-r border-gov-950">
          {/* Branding */}
          <div className="px-5 pt-5 pb-4 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="text-ka-gold-400 shrink-0">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-10 h-10" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="3" />
                  <path d="M12 2v20M2 12h20M4.93 4.93l14.14 14.14M4.93 19.07L19.07 4.93" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-base font-extrabold leading-tight tracking-wide truncate">Nyaya Marga</div>
                <div className="text-sm font-semibold text-ka-gold-300 tracking-wide leading-tight">ನ್ಯಾಯ ಮಾರ್ಗ</div>
              </div>
            </div>
            <p className="mt-2 text-[10px] font-bold text-white/40 uppercase tracking-[0.14em]">Court Case Monitoring System</p>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-4" aria-label="Main navigation">
            {NAV_SECTIONS.map((section) => (
              <div key={section.heading}>
                <h4 className="text-[10px] font-bold text-white/30 uppercase tracking-[0.14em] mb-1.5 px-3">{section.heading}</h4>
                <ul className="space-y-0.5">
                  {section.items.map((item) => {
                    const active = isActive(item.href, item.exact);
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          className={`flex items-center gap-2.5 px-3 py-2 text-[13px] font-medium transition-all duration-150 group border-l-[3px] ${
                            active
                              ? 'bg-white/10 text-white border-ka-gold-400'
                              : 'text-white/50 hover:bg-white/5 hover:text-white/80 border-transparent'
                          }`}
                          aria-current={active ? 'page' : undefined}
                        >
                          <item.icon className={`w-4 h-4 shrink-0 ${active ? 'text-ka-gold-400' : 'text-white/30 group-hover:text-white/50'}`} />
                          <span className="truncate">{item.label}</span>
                          {active && <ChevronRight className="w-3 h-3 ml-auto text-white/20" />}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </nav>

          {/* Footer */}
          <div className="shrink-0">
            <div className="px-4 py-3 border-t border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2 text-[10px] text-white/30 font-semibold uppercase tracking-wider">
                <ShieldCheck className="w-3.5 h-3.5" /><span>Centre for e-Governance</span>
              </div>
              <button className="text-white/20 hover:text-white/60 transition-colors" aria-label="Log out" title="Log Out">
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="h-1 w-full flex" aria-hidden="true">
              <div className="flex-1 bg-[#FF9933]" /><div className="flex-1 bg-white" /><div className="flex-1 bg-[#138808]" />
            </div>
          </div>
        </aside>

        {/* MAIN AREA */}
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-12 shrink-0 bg-white border-b border-slate-200 flex items-center justify-between px-6 z-10">
            <div className="flex items-center gap-2 text-[11px] font-bold tracking-[0.1em] text-gov-800 uppercase">
              <ShieldCheck className="w-3.5 h-3.5 text-ka-green-600" />
              <span>Govt. of Karnataka · Secure Departmental Network</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-[13px] font-semibold text-slate-800 leading-none">Authorized Officer</div>
                <div className="text-[11px] font-medium text-slate-400 mt-0.5">Centre for e-Governance</div>
              </div>
              <div className="w-8 h-8 bg-gov-800 flex items-center justify-center text-[11px] font-bold text-white border-2 border-ka-gold-400" aria-label="User avatar">AO</div>
            </div>
          </header>
          <main id="main-content" className="flex-1 overflow-y-auto p-6 lg:p-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
