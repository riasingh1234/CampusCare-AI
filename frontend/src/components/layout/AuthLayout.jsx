import { Building2 } from 'lucide-react';

function CampusMap() {
  const pin = { transformBox: 'fill-box', transformOrigin: 'center' };
  return (
    <svg viewBox="0 0 520 380" className="w-full" role="img" aria-label="Illustrated campus map showing where issues are reported">
      <g stroke="#243653" strokeWidth="14" strokeLinecap="round">
        <path d="M20 190H500" /><path d="M180 20V360" /><path d="M360 20V360" />
      </g>
      <g fill="#162540" stroke="#33486B" strokeWidth="1.5">
        <rect x="40" y="40" width="110" height="120" rx="10" /><rect x="210" y="40" width="120" height="90" rx="10" />
        <rect x="390" y="40" width="100" height="120" rx="10" /><rect x="40" y="220" width="110" height="110" rx="10" />
        <rect x="210" y="220" width="120" height="110" rx="10" /><rect x="390" y="230" width="100" height="100" rx="10" />
      </g>
      <g fill="#667DA3" fontSize="12" fontWeight="600" textAnchor="middle">
        <text x="95" y="108">Block A</text><text x="270" y="90">Library</text><text x="440" y="108">Hostel</text>
        <text x="95" y="280">Cafeteria</text><text x="270" y="280">Sports</text><text x="440" y="285">Admin</text>
      </g>
      <g>
        <circle cx="120" cy="64" r="8" fill="#F87171" className="motion-safe:animate-ping" style={pin} />
        <circle cx="120" cy="64" r="6" fill="#EF4444" />
        <circle cx="300" cy="190" r="6" fill="#5589F5" />
        <circle cx="230" cy="250" r="6" fill="#FBBF24" />
        <circle cx="440" cy="150" r="6" fill="#34D399" />
      </g>
      <g fontSize="11" fontWeight="700">
        <rect x="132" y="44" width="104" height="26" rx="6" fill="#fff" /><text x="184" y="61" textAnchor="middle" fill="#0B1B33">Sparking fan</text>
        <rect x="312" y="170" width="92" height="26" rx="6" fill="#fff" /><text x="358" y="187" textAnchor="middle" fill="#0B1B33">Wi-Fi outage</text>
        <rect x="242" y="236" width="86" height="26" rx="6" fill="#fff" /><text x="285" y="253" textAnchor="middle" fill="#0B1B33">Leaking tap</text>
        <rect x="396" y="132" width="86" height="26" rx="6" fill="#fff" /><text x="439" y="149" textAnchor="middle" fill="#0B1B33">Fixed today</text>
      </g>
    </svg>
  );
}

export default function AuthLayout({ children }) {
  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[1.05fr_1fr]">
      <section className="hidden flex-col justify-between bg-navy-900 p-12 text-white lg:flex">
        <div className="flex items-center gap-2.5">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-navy-900"><Building2 className="h-5 w-5" /></span>
          <span className="text-lg font-extrabold">CampusCare<span className="ml-1 rounded bg-brand-500 px-1.5 py-0.5 align-middle text-[10px] font-bold">AI</span></span>
        </div>
        <div>
          <h2 className="max-w-md text-4xl font-extrabold leading-tight">Every campus fix, tracked from report to resolved.</h2>
          <p className="mt-4 max-w-md text-[15px] leading-relaxed text-navy-200">Report a problem in under a minute, follow its progress, and see who is working on it.</p>
          <div className="mt-8 max-w-lg"><CampusMap /></div>
        </div>
        <p className="text-[13px] text-navy-300">Stage 1 preview: runs on local sample data in your browser.</p>
      </section>
      <section className="flex items-center justify-center px-5 py-10 sm:px-10">
        <div className="w-full max-w-md">{children}</div>
      </section>
    </div>
  );
}
