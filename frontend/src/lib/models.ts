import { z } from 'zod'

export const Me=z.object({id:z.string().uuid(),email:z.string().nullable().optional(),workspace_id:z.string().uuid(),display_name:z.string()})
export const Member=z.object({user_id:z.string().uuid(),display_name:z.string()})
export const Settings=z.object({workspace_id:z.string().uuid(),project_name:z.string(),description:z.string().nullable().optional(),stage:z.string().nullable().optional(),next_result:z.string().nullable().optional(),landing_url:z.string().nullable().optional(),telegram_url:z.string().nullable().optional(),presentation_file_id:z.string().uuid().nullable().optional(),updated_at:z.string()}).passthrough()
export const Task=z.object({id:z.string().uuid(),title:z.string(),description:z.string().nullable().optional(),assignee_id:z.string().uuid().nullable().optional(),status:z.enum(['planned','in_progress','done']),due_date:z.string().nullable().optional(),planned_week:z.string().nullable().optional(),blocked:z.boolean(),block_reason:z.string().nullable().optional(),updated_at:z.string()}).passthrough()
export const Program=z.object({id:z.string().uuid(),name:z.string(),url:z.string().nullable().optional(),deadline:z.string().nullable().optional(),status:z.enum(['considering','preparing','submitted','next_stage','accepted','rejected']),next_step:z.string().nullable().optional(),notes:z.string().nullable().optional(),archived:z.boolean(),updated_at:z.string()}).passthrough()
export const Answer=z.object({id:z.string().uuid(),question:z.string(),answer:z.string(),keywords:z.string(),updated_at:z.string()}).passthrough()
export const FileRow=z.object({id:z.string().uuid(),display_name:z.string(),original_name:z.string(),mime_type:z.string(),size_bytes:z.number(),scope:z.enum(['project','program']),program_id:z.string().uuid().nullable().optional(),created_at:z.string()}).passthrough()
export const Meeting=z.object({id:z.string().uuid(),title:z.string(),meeting_date:z.string(),notes:z.string(),updated_at:z.string()}).passthrough()
export const Decision=z.object({id:z.string().uuid(),title:z.string(),text:z.string(),decision_date:z.string(),meeting_id:z.string().uuid().nullable().optional(),archived:z.boolean(),updated_at:z.string()}).passthrough()
export const Dashboard=z.object({settings:Settings.nullable(),focus:z.array(z.object({id:z.string(),text:z.string(),week_start:z.string(),done:z.boolean()}).passthrough()),tasks:z.array(Task),programs:z.array(Program),decisions:z.array(Decision),today:z.string()})
export type TaskRow=z.infer<typeof Task>
export type ProgramRow=z.infer<typeof Program>
