import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const source = path.join(root, 'src', 'generated-art')
const target = path.join(root, 'public', 'art')
const names = ['home', 'side', 'wide', 'rail']

await mkdir(target, { recursive: true })

for (const name of names) {
  const encoded = (await readFile(path.join(source, `${name}.webp.b64`), 'utf8')).trim()
  await writeFile(path.join(target, `${name}.webp`), Buffer.from(encoded, 'base64'))
}
