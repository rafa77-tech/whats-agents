'use client'

import { useEffect, useRef } from 'react'
import { MessageBubble, type Message } from './message-bubble'

interface Props {
  messages: Message[]
}

export function MessageList({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Nenhuma mensagem ainda
      </div>
    )
  }

  // Group messages by date
  const groupedMessages: { date: string; messages: Message[] }[] = []
  let currentDate = ''

  messages.forEach((msg) => {
    const msgDate = new Date(msg.created_at).toLocaleDateString('pt-BR')
    if (msgDate !== currentDate) {
      currentDate = msgDate
      groupedMessages.push({ date: msgDate, messages: [] })
    }
    const lastGroup = groupedMessages[groupedMessages.length - 1]
    if (lastGroup) {
      lastGroup.messages.push(msg)
    }
  })

  return (
    <div className="space-y-4 p-4">
      {groupedMessages.map((group) => (
        <div key={group.date}>
          <div className="mb-4 flex justify-center">
            <span className="rounded-full bg-muted px-3 py-1 text-xs">{group.date}</span>
          </div>
          <div className="space-y-2">
            {group.messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
