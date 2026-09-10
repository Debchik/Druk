import { describe, expect, it } from 'vitest'
import { weekStart } from './date'
describe('weekStart',()=>{it('returns Monday',()=>expect(weekStart(new Date('2026-09-09T12:00:00Z'))).toBe('2026-09-07'))})
