import type { TemplateComponent } from '@/types/meta'
import { cn } from '@/lib/utils'

interface WhatsAppPreviewProps {
  components?: TemplateComponent[] | undefined
  className?: string
}

function highlightVariables(text: string): React.ReactNode {
  const parts = text.split(/(\{\{\d+\}\})/)
  return parts.map((part, i) => {
    if (/\{\{\d+\}\}/.test(part)) {
      return (
        <span key={i} className="rounded bg-state-ai px-0.5 font-medium text-state-ai-foreground">
          {part}
        </span>
      )
    }
    return part
  })
}

export function WhatsAppPreview({ components, className }: WhatsAppPreviewProps) {
  if (!components || components.length === 0) {
    return (
      <div
        className={cn(
          'flex items-center justify-center rounded-xl bg-[#e5ddd5] p-4 dark:bg-[#0b141a]',
          className
        )}
      >
        <p className="text-xs text-muted-foreground">Sem preview</p>
      </div>
    )
  }

  const header = components.find((c) => c.type === 'HEADER')
  const body = components.find((c) => c.type === 'BODY')
  const footer = components.find((c) => c.type === 'FOOTER')
  const buttons = components.find((c) => c.type === 'BUTTONS')

  return (
    <div
      className={cn(
        'flex flex-col items-end rounded-xl bg-[#e5ddd5] p-4 dark:bg-[#0b141a]',
        className
      )}
    >
      {/* Message bubble */}
      <div className="max-w-[240px] rounded-lg rounded-tr-none bg-[#dcf8c6] px-3 py-2 shadow-sm dark:bg-[#005c4b]">
        {header?.text && (
          <p className="mb-1 text-xs font-bold text-gray-900 dark:text-gray-100">
            {highlightVariables(header.text)}
          </p>
        )}
        {body?.text && (
          <p className="whitespace-pre-wrap text-[13px] leading-snug text-gray-900 dark:text-gray-100">
            {highlightVariables(body.text)}
          </p>
        )}
        {footer?.text && (
          <p className="mt-1 text-[11px] text-gray-500 dark:text-gray-400">{footer.text}</p>
        )}
        <p className="mt-0.5 text-right text-[10px] text-gray-500 dark:text-gray-400">14:32</p>
      </div>

      {/* Quick reply buttons */}
      {buttons?.buttons && buttons.buttons.length > 0 && (
        <div className="mt-1 flex max-w-[240px] gap-1">
          {buttons.buttons.map((btn, i) => (
            <div
              key={i}
              className="flex-1 rounded-lg bg-white py-1.5 text-center text-[12px] font-medium text-[#00a884] shadow-sm dark:bg-[#1f2c34] dark:text-[#00a884]"
            >
              {btn.text}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
