import type { Lang } from '../contexts/LanguageContext'

const strings = {
  maintenanceTask:   { en: 'Maintenance Task',                                        zh: '维护任务' },
  issue:             { en: 'Issue',                                                    zh: '问题' },
  clickupStatus:     { en: 'ClickUp status:',                                         zh: 'ClickUp 状态:' },
  actionItems:       { en: 'Action Items',                                             zh: '待办事项' },
  arrivalDateTime:   { en: 'Arrival Date & Time',                                     zh: '到达日期和时间' },
  tapToSetArrival:   { en: 'Tap to set arrival time',                                 zh: '点击设置到达时间' },
  completionStatus:  { en: 'Completion Status',                                        zh: '完成状态' },
  statusPending:     { en: 'Pending',                                                  zh: '待处理' },
  statusInProgress:  { en: 'In Progress',                                              zh: '进行中' },
  statusCompleted:   { en: 'Completed',                                                zh: '已完成' },
  technicianNotes:   { en: 'Technician Notes',                                         zh: '技术员备注' },
  notesPlaceholder:  { en: 'Add notes about this task...',                             zh: '添加此任务的备注...' },
  autoSaved:         { en: 'Auto-saved when you leave this field',                    zh: '离开此字段时自动保存' },
  uploading:         { en: 'Uploading...',                                             zh: '上传中...' },
  tapToAttach:       { en: 'Tap to attach a photo or file',                           zh: '点击附加照片或文件' },
  dragDrop:          { en: 'or drag and drop',                                         zh: '或拖放' },
  attachments:       { en: 'Attachments',                                              zh: '附件' },
  viewWorkOrderPdf:  { en: 'View Work Order PDF',                                      zh: '查看工单 PDF' },
  opensInNewTab:     { en: 'Opens in new tab',                                         zh: '在新标签页打开' },
  saving:            { en: 'Saving...',                                                zh: '保存中...' },
  saved:             { en: '✓ Saved',                                                  zh: '✓ 已保存' },
  errorPrefix:       { en: 'Error',                                                    zh: '错误' },
  cachedData:        { en: 'Showing cached data — ClickUp may be temporarily unavailable.', zh: '显示缓存数据 — ClickUp 可能暂时不可用。' },
  unableToLoad:      { en: 'Unable to load task',                                      zh: '无法加载任务' },
  scheduledWindow:   { en: 'Scheduled Window',                                         zh: '预约时间窗口' },
  to:                { en: 'to',                                                        zh: '至' },
  hrBuffer:          { en: 'hr buffer',                                                 zh: '小时缓冲' },
  translating:       { en: 'Translating...',                                            zh: '翻译中...' },
  pdfMayBeOutdated:       { en: 'PDF may be outdated. Changed since last generation:',  zh: 'PDF 可能已过期。上次生成后发生变更：' },
  regeneratePdf:          { en: 'Regenerate PDF',                                       zh: '重新生成 PDF' },
  regenerating:           { en: 'Regenerating...',                                      zh: '重新生成中...' },
  pdfRegenerated:         { en: '✓ PDF regenerated and email resent',                   zh: '✓ PDF 已重新生成并重新发送邮件' },
  fieldTaskName:          { en: 'Task Name',                                            zh: '任务名称' },
  fieldPropertyAddress:   { en: 'Property Address',                                     zh: '物业地址' },
  fieldIssueDescription:  { en: 'Issue Description',                                    zh: '问题描述' },
  fieldActionItems:       { en: 'Action Items',                                         zh: '待办事项' },
  fieldScheduledDate:     { en: 'Scheduled Date',                                       zh: '预约日期' },
} as const

export type StringKey = keyof typeof strings

export function t(key: StringKey, lang: Lang): string {
  return strings[key][lang]
}
