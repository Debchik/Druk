const artUrl=(name:string)=>`url("${import.meta.env.BASE_URL}art/${name}.webp?v=20260913-1")`

export function applyGeneratedArtwork(){
  const root=document.documentElement
  root.style.setProperty('--druk-art-home',artUrl('home'))
  root.style.setProperty('--druk-art-side',artUrl('side'))
  root.style.setProperty('--druk-art-wide',artUrl('wide'))
  root.style.setProperty('--druk-art-rail',artUrl('rail'))
}
