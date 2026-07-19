<template>
  <figure class="campus-photo" :class="[`campus-photo--${fit}`, `campus-photo--${position}`]">
    <img :src="src" :alt="alt" />
    <figcaption v-if="caption">{{ caption }}</figcaption>
  </figure>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  src: string
  alt: string
  caption?: string
  fit?: 'cover' | 'contain'
  position?: 'center' | 'left' | 'right'
}>(), {
  caption: '',
  fit: 'cover',
  position: 'center',
})
</script>

<style scoped>
.campus-photo {
  position: relative;
  display: block;
  width: 100%;
  margin: 0;
  overflow: hidden;
  pointer-events: none;
}

.campus-photo::after {
  position: absolute;
  inset: 0;
  content: '';
  background: linear-gradient(180deg, rgba(247, 251, 255, 0) 32%, rgba(247, 251, 255, .9) 92%, #f7fbff 100%);
}

.campus-photo img {
  display: block;
  width: 100%;
  height: 100%;
  opacity: .26;
  object-position: center;
  filter: grayscale(1) sepia(1) saturate(5.5) hue-rotate(174deg) brightness(1.24) contrast(.88);
  mix-blend-mode: multiply;
  -webkit-mask-image: linear-gradient(180deg, transparent 0, #000 15%, #000 72%, transparent 100%);
  mask-image: linear-gradient(180deg, transparent 0, #000 15%, #000 72%, transparent 100%);
}

.campus-photo--cover img { object-fit: cover; }
.campus-photo--contain img { object-fit: contain; }
.campus-photo--left img { object-position: left center; }
.campus-photo--right img { object-position: right center; }

.campus-photo figcaption {
  position: absolute;
  right: 0;
  bottom: 5px;
  left: 0;
  z-index: 1;
  color: var(--brand);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .04em;
  text-align: center;
}

:global(html.dark .campus-photo)::after {
  background: linear-gradient(180deg, rgba(12, 20, 32, 0) 28%, rgba(12, 20, 32, .9) 92%, #0c1420 100%);
}

:global(html.dark .campus-photo img) {
  opacity: .18;
  filter: grayscale(1) sepia(1) saturate(4) hue-rotate(175deg) brightness(.9) contrast(1.1);
  mix-blend-mode: screen;
}
</style>
