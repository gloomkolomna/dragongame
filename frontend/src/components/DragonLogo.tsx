function DragonLogo({ width = 120, height = 120 }: { width?: number; height?: number }) {
  return (
    <svg width={width} height={height} viewBox="0 0 240 200" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="g"><feGaussianBlur stdDeviation="3"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <filter id="s"><feGaussianBlur stdDeviation="5"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <radialGradient id="halo"><stop offset="0%" stopColor="rgba(100,200,255,0.12)"/><stop offset="100%" stopColor="transparent"/></radialGradient>
        <radialGradient id="firePlasma"><stop offset="0%" stopColor="#8844ff"/><stop offset="50%" stopColor="#44aaff"/><stop offset="100%" stopColor="transparent"/></radialGradient>
      </defs>

      <ellipse cx="120" cy="100" rx="90" ry="55" fill="url(#halo)" filter="url(#s)"/>

      {/* === PURPLE PLASMA BLAST (Беззубик стреляет) === */}
      <ellipse cx="55" cy="78" rx="30" ry="12" fill="url(#firePlasma)" filter="url(#s)" opacity="0.6"/>

      {/* === TAIL — long, sweeping, with red prosthetic fin === */}
      <path d="M190 115 Q215 105 225 115 Q235 125 228 135" fill="none" stroke="#1a1a24" strokeWidth="9" strokeLinecap="round" filter="url(#g)"/>
      <path d="M190 115 Q215 105 225 115" fill="none" stroke="#252535" strokeWidth="6" strokeLinecap="round"/>
      {/* Red prosthetic tail fin */}
      <path d="M225 115 L235 105 L232 112 L240 110 L234 116 L240 120 L232 118 L235 125 Z" fill="#cc2222" filter="url(#g)"/>
      <path d="M225 115 L235 105 L232 112 L240 110 L234 116 L240 120 L232 118 L235 125 Z" fill="#ee4444" opacity="0.7"/>

      {/* === HIND LEGS — cat-like, crouching === */}
      <path d="M165 135 L170 158 Q172 168 178 168 L174 168 Q164 168 162 155 L160 135" fill="#111118"/>
      <ellipse cx="168" cy="170" rx="12" ry="4" fill="#111118"/>
      <path d="M158 170 L155 176 M164 172 L161 178 M168 172 L166 178 M174 170 L174 176 M178 170 L180 176" stroke="#333" strokeWidth="1.2" strokeLinecap="round"/>

      {/* === BODY — sleek, muscular, black === */}
      <ellipse cx="155" cy="120" rx="38" ry="26" fill="#15151f" filter="url(#g)"/>
      <ellipse cx="155" cy="118" rx="36" ry="24" fill="#1e1e2a"/>
      {/* subtle belly highlight */}
      <ellipse cx="153" cy="128" rx="22" ry="10" fill="#2a2a3a" opacity="0.4"/>

      {/* === FRONT LEGS === */}
      <path d="M128 130 L120 156 Q118 168 125 168 L120 167 Q112 167 114 155 L120 130" fill="#111118"/>
      <ellipse cx="122" cy="169" rx="11" ry="4" fill="#111118"/>
      <path d="M112 169 L109 175 M118 171 L115 177 M122 171 L120 177 M126 170 L126 175 M130 169 L132 174" stroke="#333" strokeWidth="1.2" strokeLinecap="round"/>

      {/* === NECK — thick, smooth === */}
      <path d="M136 105 Q120 85 110 72" fill="none" stroke="#1a1a24" strokeWidth="18" strokeLinecap="round" filter="url(#g)"/>
      <path d="M136 105 Q120 85 110 72" fill="none" stroke="#1e1e2a" strokeWidth="14" strokeLinecap="round"/>

      {/* === HEAD — rounded, blunt, cat-like === */}
      <ellipse cx="108" cy="70" rx="24" ry="20" fill="#1a1a24" filter="url(#g)"/>
      <ellipse cx="108" cy="70" rx="22" ry="18" fill="#222230"/>

      {/* === EARS / ear-plates (Беззубик's signature flaps) === */}
      <path d="M90 56 Q80 40 72 32 Q78 36 85 48 Z" fill="#1a1a24" filter="url(#g)"/>
      <path d="M125 54 Q132 38 140 30 Q135 34 128 46 Z" fill="#1a1a24" filter="url(#g)"/>
      {/* inner ear glow */}
      <path d="M88 52 Q82 42 76 36 Z" fill="#333" opacity="0.5"/>
      <path d="M126 50 Q131 40 136 34 Z" fill="#333" opacity="0.5"/>

      {/* === EYES — huge, expressive, green-yellow === */}
      <ellipse cx="98" cy="66" rx="8" ry="9" fill="#44cc44" filter="url(#g)"/>
      <ellipse cx="98" cy="66" rx="4" ry="8.5" fill="#0a0a0a"/>
      <ellipse cx="99" cy="64" rx="2" ry="2" fill="#fff" opacity="0.7"/>

      <ellipse cx="118" cy="65" rx="8" ry="9" fill="#44cc44" filter="url(#g)"/>
      <ellipse cx="118" cy="65" rx="4" ry="8.5" fill="#0a0a0a"/>
      <ellipse cx="119" cy="63" rx="2" ry="2" fill="#fff" opacity="0.7"/>

      {/* === SNOUT — small, blunt (no teeth, hence the name!) === */}
      <ellipse cx="88" cy="72" rx="10" ry="7" fill="#1e1e2a"/>
      <ellipse cx="84" cy="72" rx="5" ry="4" fill="#252535"/>
      {/* nostrils */}
      <ellipse cx="80" cy="71" rx="2" ry="1.5" fill="#0a0a0a" opacity="0.6"/>
      <ellipse cx="83" cy="70" rx="1.5" ry="1.2" fill="#0a0a0a" opacity="0.4"/>
      {/* tiny plasma glow from mouth */}
      <ellipse cx="80" cy="74" rx="8" ry="4" fill="rgba(100,150,255,0.3)" filter="url(#g)"/>

      {/* === SPINAL SCALES — small, rounded bumps === */}
      {[0,1,2,3,4,5,6].map((i) => (
        <ellipse key={`sp${i}`} cx={118+i*9} cy={100-(i%3)*4} rx="3" ry="2" fill="#252535"/>
      ))}
      {[0,1,2,3].map((i) => (
        <ellipse key={`sp2${i}`} cx={100+i*8} cy={82-(i%2)*3} rx="2.5" ry="1.8" fill="#252535"/>
      ))}

      {/* === WINGS — huge, bat-like, extended === */}
      {/* Left wing */}
      <path d="M140 108 L105 80 L75 50 Q65 35 55 25 Q45 15 50 22 Q40 8 55 14 Q42 0 58 10 L62 18 Q75 8 88 20 L92 28 Q100 18 108 30 L112 38 Q118 28 125 40 L120 52 Q127 48 132 58 L130 65 Q135 62 138 72 L135 80 Z"
            fill="rgba(20,20,30,0.7)" stroke="#252535" strokeWidth="1" filter="url(#g)"/>
      {/* Right wing */}
      <path d="M170 108 L200 80 L225 50 Q235 40 240 30 Q246 20 242 25 Q250 12 240 18 Q252 5 238 14 L234 20 Q220 10 212 22 L208 28 Q200 20 195 32 L192 38 Q185 30 178 42 L180 55 Q175 50 170 60 L172 68 Q168 64 165 74 L168 82 Z"
            fill="rgba(20,20,30,0.7)" stroke="#252535" strokeWidth="1" filter="url(#g)"/>
      {/* wing membrane vein lines */}
      {['M105 80 L85 45','M110 75 L95 40','M118 55 L110 35','M125 40 L118 28'].map((d,i) => (
        <path key={`lv${i}`} d={d} fill="none" stroke="#333" strokeWidth="0.8" opacity="0.5"/>
      ))}
      {['M200 80 L220 45','M195 75 L210 40','M188 55 L195 35','M180 40 L188 28'].map((d,i) => (
        <path key={`rv${i}`} d={d} fill="none" stroke="#333" strokeWidth="0.8" opacity="0.5"/>
      ))}
    </svg>
  );
}

export default DragonLogo;
