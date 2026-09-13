import type { ReactNode } from 'react'

function inline(text:string,key='i'):ReactNode[]{
  const pattern=/(\*\*[^*]+\*\*|~~[^~]+~~|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^)]+\)|\*[^*]+\*)/g
  const out:ReactNode[]=[];let last=0,n=0
  for(const m of text.matchAll(pattern)){
    const index=m.index??0;if(index>last)out.push(text.slice(last,index));const token=m[0],k=`${key}-${n++}`
    if(token.startsWith('**'))out.push(<strong key={k}>{token.slice(2,-2)}</strong>)
    else if(token.startsWith('~~'))out.push(<del key={k}>{token.slice(2,-2)}</del>)
    else if(token.startsWith('`'))out.push(<code key={k}>{token.slice(1,-1)}</code>)
    else if(token.startsWith('[')){const mm=token.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/);out.push(mm?<a key={k} href={mm[2]} target="_blank" rel="noreferrer">{mm[1]}</a>:token)}
    else out.push(<em key={k}>{token.slice(1,-1)}</em>)
    last=index+token.length
  }
  if(last<text.length)out.push(text.slice(last));return out
}
function cells(line:string){return line.trim().replace(/^\||\|$/g,'').split('|').map(x=>x.trim())}
function isSep(line:string){return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line)}

export default function Markdown({text,compact=false}:{text:string;compact?:boolean}){
  const lines=(text||'').replace(/\r\n/g,'\n').split('\n'),blocks:ReactNode[]=[];let i=0
  while(i<lines.length){
    const line=lines[i]
    if(!line.trim()){i++;continue}
    if(line.trim().startsWith('```')){const lang=line.trim().slice(3).trim(),buf:string[]=[];i++;while(i<lines.length&&!lines[i].trim().startsWith('```'))buf.push(lines[i++]);if(i<lines.length)i++;blocks.push(<pre key={`b${i}`}><code data-lang={lang||undefined}>{buf.join('\n')}</code></pre>);continue}
    if(i+1<lines.length&&line.includes('|')&&isSep(lines[i+1])){const head=cells(line),rows:string[][]=[];i+=2;while(i<lines.length&&lines[i].includes('|')&&lines[i].trim()){rows.push(cells(lines[i++]));}blocks.push(<div className="markdown-table-wrap" key={`b${i}`}><table><thead><tr>{head.map((c,j)=><th key={j}>{inline(c,`h${j}`)}</th>)}</tr></thead><tbody>{rows.map((r,ri)=><tr key={ri}>{head.map((_,ci)=><td key={ci}>{inline(r[ci]||'',`r${ri}c${ci}`)}</td>)}</tr>)}</tbody></table></div>);continue}
    const h=line.match(/^(#{1,4})\s+(.+)$/);if(h){const level=Math.min(h[1].length,4),content=inline(h[2],`h${i}`);blocks.push(level===1?<h1 key={i}>{content}</h1>:level===2?<h2 key={i}>{content}</h2>:level===3?<h3 key={i}>{content}</h3>:<h4 key={i}>{content}</h4>);i++;continue}
    if(/^\s*[-*+]\s+/.test(line)){const items:string[]=[];while(i<lines.length&&/^\s*[-*+]\s+/.test(lines[i]))items.push(lines[i++].replace(/^\s*[-*+]\s+/,''));blocks.push(<ul key={`b${i}`}>{items.map((x,j)=><li key={j}>{inline(x,`u${i}-${j}`)}</li>)}</ul>);continue}
    if(/^\s*\d+[.)]\s+/.test(line)){const items:string[]=[];while(i<lines.length&&/^\s*\d+[.)]\s+/.test(lines[i]))items.push(lines[i++].replace(/^\s*\d+[.)]\s+/,''));blocks.push(<ol key={`b${i}`}>{items.map((x,j)=><li key={j}>{inline(x,`o${i}-${j}`)}</li>)}</ol>);continue}
    if(/^\s*>\s?/.test(line)){const q:string[]=[];while(i<lines.length&&/^\s*>\s?/.test(lines[i]))q.push(lines[i++].replace(/^\s*>\s?/,''));blocks.push(<blockquote key={`b${i}`}>{q.map((x,j)=><div key={j}>{inline(x,`q${i}-${j}`)}</div>)}</blockquote>);continue}
    const para=[line.trim()];i++;while(i<lines.length&&lines[i].trim()&&!lines[i].trim().startsWith('```')&&!/^(#{1,4})\s+/.test(lines[i])&&!/^\s*[-*+]\s+/.test(lines[i])&&!/^\s*\d+[.)]\s+/.test(lines[i])&&!/^\s*>\s?/.test(lines[i])&&!(i+1<lines.length&&lines[i].includes('|')&&isSep(lines[i+1])))para.push(lines[i++].trim())
    blocks.push(<p key={`b${i}`}>{inline(para.join(' '),`p${i}`)}</p>)
  }
  return <div className={`markdown-body${compact?' compact':''}`}>{blocks.length?blocks:<span className="muted">Ответ пока пуст.</span>}</div>
}
