<template>
  <svg class="campus-robot" viewBox="0 0 460 270" role="img" aria-label="河海智问智能助手">
    <defs>
      <linearGradient id="robot-blue" x1="0" y1="0" x2="1" y2="1">
        <stop stop-color="#66adff" />
        <stop offset="1" stop-color="#075fd1" />
      </linearGradient>
      <linearGradient id="robot-face" x1="0" y1="0" x2="0" y2="1">
        <stop stop-color="#1982ef" />
        <stop offset="1" stop-color="#063caa" />
      </linearGradient>
      <filter id="robot-shadow" x="-30%" y="-30%" width="160%" height="180%">
        <feDropShadow dx="0" dy="10" stdDeviation="10" flood-color="#276fca" flood-opacity=".2" />
      </filter>
    </defs>
    <circle cx="230" cy="135" r="108" fill="#eef6ff" />
    <g fill="#dcecff">
      <path d="M65 91h58a18 18 0 0 1 18 18v13a18 18 0 0 1-18 18H97l-16 15 3-15H65a18 18 0 0 1-18-18v-13a18 18 0 0 1 18-18z" />
      <path d="M337 70h57a18 18 0 0 1 18 18v12a18 18 0 0 1-18 18h-13l3 14-17-14h-30a18 18 0 0 1-18-18V88a18 18 0 0 1 18-18z" />
    </g>
    <g fill="#fff"><circle cx="83" cy="115" r="5" /><circle cx="99" cy="115" r="5" /><circle cx="115" cy="115" r="5" /><circle cx="348" cy="94" r="5" /><circle cx="364" cy="94" r="5" /><circle cx="380" cy="94" r="5" /></g>
    <g filter="url(#robot-shadow)">
      <path d="M174 165c8-32 25-47 56-47s49 15 57 47l10 51c-23 17-113 17-136 0z" fill="#fff" stroke="#8ec0f7" stroke-width="3" />
      <path d="M174 170c-25 1-39 13-44 35" fill="none" stroke="#fff" stroke-linecap="round" stroke-width="20" />
      <path d="M286 170c24 1 38 13 43 35" fill="none" stroke="#fff" stroke-linecap="round" stroke-width="20" />
      <circle cx="127" cy="210" r="12" fill="url(#robot-blue)" />
      <circle cx="333" cy="210" r="12" fill="url(#robot-blue)" />
      <rect x="161" y="73" width="138" height="94" rx="45" fill="#fff" stroke="#8ec0f7" stroke-width="3" />
      <rect x="174" y="88" width="112" height="66" rx="29" fill="url(#robot-face)" />
      <circle cx="207" cy="119" r="8" fill="#fff" /><circle cx="253" cy="119" r="8" fill="#fff" />
      <path d="M214 137c9 8 23 8 32 0" fill="none" stroke="#fff" stroke-linecap="round" stroke-width="5" />
      <path d="M230 73V48" stroke="#6daeff" stroke-linecap="round" stroke-width="5" />
      <circle cx="230" cy="42" r="9" fill="url(#robot-blue)" />
      <circle cx="230" cy="188" r="25" fill="#edf6ff" stroke="#8ec0f7" stroke-width="2" />
      <path d="M230 170l5 12 13 1-10 8 3 13-11-7-11 7 3-13-10-8 13-1z" fill="#1474df" />
    </g>
    <g fill="#a9cdf8"><path d="M118 58l4 10 10 4-10 4-4 10-4-10-10-4 10-4z" /><path d="M342 35l4 10 10 4-10 4-4 10-4-10-10-4 10-4z" /><path d="M365 156l3 8 8 3-8 3-3 8-3-8-8-3 8-3z" /></g>
  </svg>
</template>

<style scoped>
.campus-robot{display:block;width:100%;height:auto;overflow:visible}
</style>
