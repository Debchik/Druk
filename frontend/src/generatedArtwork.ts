import home from './generated-art/home.webp.b64?raw'
import side from './generated-art/side.webp.b64?raw'
import wide from './generated-art/wide.webp.b64?raw'
import rail from './generated-art/rail.webp.b64?raw'

const dataUrl=(value:string)=>`url("data:image/webp;base64,${value.trim()}")`

export function applyGeneratedArtwork(){
  const root=document.documentElement
  root.style.setProperty('--druk-art-home',dataUrl(home))
  root.style.setProperty('--druk-art-side',dataUrl(side))
  root.style.setProperty('--druk-art-wide',dataUrl(wide))
  root.style.setProperty('--druk-art-rail',dataUrl(rail))
}
