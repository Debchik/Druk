import type { ReactNode } from 'react'

type InlineToken={raw:string;kind:'image'|'link'|'autolink'|'bold'|'strike'|'highlight'|'code'|'italic'|'wiki';a?:string;b?:string}

function tokenAt(text:string):InlineToken|null{
  const rules:Array<[RegExp,(m:RegExpMatchArray)=>InlineToken]>=[
    [/^!\[([^\]]*)\]\((https?:\/\/[^)\s]+)\)/,m=>({raw:m[0],kind:'image',a:m[1],b:m[2]})],
    [/^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/,m=>({raw:m[0],kind:'link',a:m[1],b:m[2]})],
    [/^<(https?:\/\/[^>\s]+)>/,m=>({raw:m[0],kind:'autolink',a:m[1]})],
    [/^\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/,m=>({raw:m[0],kind:'wiki',a:m[2]||m[1],b:m[1]})],
    [/^\*\*(.+?)\*\*/,m=>({raw:m[0],kind:'bold',a:m[1]})],
    [/^__(.+?)__/,m=>({raw:m[0],kind:'bold',a:m[1]})],
    [/^~~(.+?)~~/,m=>({raw:m[0],kind:'strike',a:m[1]})],
    [/^==(.+?)==/,m=>({raw:m[0],kind:'highlight',a:m[1]})],
    [/^`([^`]+)`/,m=>({raw:m[0],kind:'code',a:m[1]})],
    [/^\*([^*\n]+)\*/,m=>({raw:m[0],kind:'italic',a:m[1]})],
    [/^_([^_\n]+)_/,m=>({raw:m[0],kind:'italic',a:m[1]})],
  ]
  for(const [re,build] of rules){const m=text.match(re);if(m)return build(m)}
  return null
}

function inline(text:string,key='i'):ReactNode[]{
  const out:ReactNode[]=[];let plain='',n=0,i=0
  const flush=()=>{if(plain){out.push(plain);plain=''}}
  while(i<text.length){
    if(text[i]==='\\'&&i+1<text.length&&'\\`*_{}[]()#+-.!|>~='.includes(text[i+1])){plain+=text[i+1];i+=2;continue}
    const token=tokenAt(text.slice(i))
    if(!token){plain+=text[i++];continue}
    flush();const k=`${key}-${n++}`
    if(token.kind==='image')out.push(<img key={k} className="markdown-image" src={token.b} alt={token.a||''} loading="lazy"/> )
    else if(token.kind==='link')out.push(<a key={k} href={token.b} target="_blank" rel="noreferrer">{inline(token.a||'',`${k}-l`)}</a>)
    else if(token.kind==='autolink')out.push(<a key={k} href={token.a} target="_blank" rel="noreferrer">{token.a}</a>)
    else if(token.kind==='wiki')out.push(<span key={k} className="markdown-wikilink" title={token.b}>{token.a}</span>)
    else if(token.kind==='bold')out.push(<strong key={k}>{inline(token.a||'',`${k}-b`)}</strong>)
    else if(token.kind==='strike')out.push(<del key={k}>{inline(token.a||'',`${k}-s`)}</del>)
    else if(token.kind==='highlight')out.push(<mark key={k}>{inline(token.a||'',`${k}-m`)}</mark>)
    else if(token.kind==='code')out.push(<code key={k}>{token.a}</code>)
    else out.push(<em key={k}>{inline(token.a||'',`${k}-e`)}</em>)
    i+=token.raw.length
  }
  flush();return out
}

function cells(line:string){return line.trim().replace(/^\||\|$/g,'').split(/(?<!\\)\|/).map(x=>x.replace(/\\\|/g,'|').trim())}
function isSep(line:string){return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line)}
function isHr(line:string){return /^\s*((-{3,})|(\*\s*){3,}|(_\s*){3,})\s*$/.test(line)}
function isBlockStart(lines:string[],i:number){const x=lines[i]||'';return !x.trim()||x.trim().startsWith('```')||/^(#{1,6})\s+/.test(x)||/^\s*[-*+]\s+/.test(x)||/^\s*\d+[.)]\s+/.test(x)||/^\s*>\s?/.test(x)||isHr(x)||(i+1<lines.length&&x.includes('|')&&isSep(lines[i+1]))}
function paragraphParts(lines:string[],key:string){const out:ReactNode[]=[];lines.forEach((line,i)=>{const hard=/ {2,}$/.test(line)||/\\$/.test(line);const clean=hard?line.replace(/(?: {2,}|\\)$/,''):line;out.push(...inline(clean,`${key}-${i}`));if(hard&&i<lines.length-1)out.push(<br key={`${key}-br-${i}`}/>);else if(i<lines.length-1)out.push(' ') });return out}

export default function Markdown({text,compact=false}:{text:string;compact?:boolean}){
  const lines=(text||'').replace(/\r\n/g,'\n').split('\n'),blocks:ReactNode[]=[];let i=0
  while(i<lines.length){
    const line=lines[i]
    if(!line.trim()){i++;continue}

    if(line.trim().startsWith('```')){
      const lang=line.trim().slice(3).trim(),buf:string[]=[];i++
      while(i<lines.length&&!lines[i].trim().startsWith('```'))buf.push(lines[i++])
      if(i<lines.length)i++
      blocks.push(<pre className="markdown-code-block" key={`code-${i}`}><span className="markdown-code-language">{lang||'code'}</span><code data-lang={lang||undefined}>{buf.join('\n')}</code></pre>);continue
    }

    if(i+1<lines.length&&line.includes('|')&&isSep(lines[i+1])){
      const head=cells(line),rows:string[][]=[];i+=2
      while(i<lines.length&&lines[i].includes('|')&&lines[i].trim())rows.push(cells(lines[i++]))
      blocks.push(<div className="markdown-table-wrap" key={`table-${i}`}><table><thead><tr>{head.map((c,j)=><th key={j}>{inline(c,`th-${i}-${j}`)}</th>)}</tr></thead><tbody>{rows.map((r,ri)=><tr key={ri}>{head.map((_,ci)=><td key={ci}>{inline(r[ci]||'',`td-${i}-${ri}-${ci}`)}</td>)}</tr>)}</tbody></table></div>);continue
    }

    const h=line.match(/^(#{1,6})\s+(.+)$/)
    if(h){const level=h[1].length,content=inline(h[2].replace(/\s+#+\s*$/,''),`h-${i}`);blocks.push(level===1?<h1 key={i}>{content}</h1>:level===2?<h2 key={i}>{content}</h2>:level===3?<h3 key={i}>{content}</h3>:level===4?<h4 key={i}>{content}</h4>:level===5?<h5 key={i}>{content}</h5>:<h6 key={i}>{content}</h6>);i++;continue}

    if(isHr(line)){blocks.push(<hr key={`hr-${i}`}/>);i++;continue}

    if(/^\s*[-*+]\s+/.test(line)){
      const items:Array<{text:string;task?:boolean;done?:boolean}>=[]
      while(i<lines.length&&/^\s*[-*+]\s+/.test(lines[i])){
        const value=lines[i++].replace(/^\s*[-*+]\s+/,'');const task=value.match(/^\[([ xX])\]\s*(.*)$/)
        items.push(task?{text:task[2],task:true,done:task[1].toLowerCase()==='x'}:{text:value})
      }
      const taskList=items.some(x=>x.task)
      blocks.push(<ul className={taskList?'markdown-task-list':undefined} key={`ul-${i}`}>{items.map((x,j)=><li className={x.task?'markdown-task-item':undefined} key={j}>{x.task&&<input type="checkbox" checked={Boolean(x.done)} readOnly tabIndex={-1}/>}<span>{inline(x.text,`u-${i}-${j}`)}</span></li>)}</ul>);continue
    }

    if(/^\s*\d+[.)]\s+/.test(line)){
      const items:string[]=[];while(i<lines.length&&/^\s*\d+[.)]\s+/.test(lines[i]))items.push(lines[i++].replace(/^\s*\d+[.)]\s+/,''))
      blocks.push(<ol key={`ol-${i}`}>{items.map((x,j)=><li key={j}>{inline(x,`o-${i}-${j}`)}</li>)}</ol>);continue
    }

    if(/^\s*>\s?/.test(line)){
      const quote:string[]=[];while(i<lines.length&&/^\s*>\s?/.test(lines[i]))quote.push(lines[i++].replace(/^\s*>\s?/,''))
      const callout=quote[0]?.match(/^\[!([A-Za-z]+)\][+-]?\s*(.*)$/)
      if(callout){const title=callout[2]||callout[1];const rest=[...quote];rest[0]='';blocks.push(<aside className={`markdown-callout callout-${callout[1].toLowerCase()}`} key={`callout-${i}`}><b>{title}</b>{rest.filter(Boolean).map((x,j)=><div key={j}>{inline(x,`cq-${i}-${j}`)}</div>)}</aside>)}
      else blocks.push(<blockquote key={`q-${i}`}>{quote.map((x,j)=><div key={j}>{inline(x,`q-${i}-${j}`)}</div>)}</blockquote>);continue
    }

    const para=[line.trimEnd()];i++
    while(i<lines.length&&!isBlockStart(lines,i)){para.push(lines[i].trimEnd());i++}
    blocks.push(<p key={`p-${i}`}>{paragraphParts(para,`p-${i}`)}</p>)
  }
  return <div className={`markdown-body${compact?' compact':''}`}>{blocks.length?blocks:<span className="muted">Ответ пока пуст.</span>}</div>
}
