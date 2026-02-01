'use client'

import { useCallback, useRef, useState } from 'react'
import data from '@emoji-mart/data'
import Picker from '@emoji-mart/react'
import {
  Smile,
  Paperclip,
  Mic,
  Send,
  Loader2,
  X,
  Image as ImageIcon,
  FileText,
  StopCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'

interface Attachment {
  type: 'image' | 'document' | 'audio'
  file: File
  preview?: string
}

interface Props {
  onSend: (message: string, attachment?: Attachment) => Promise<void>
  disabled?: boolean
  placeholder?: string
}

export function MessageInput({ onSend, disabled, placeholder }: Props) {
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [showEmoji, setShowEmoji] = useState(false)
  const [attachment, setAttachment] = useState<Attachment | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const recordingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const handleSend = async () => {
    if ((!text.trim() && !attachment) || sending) return

    setSending(true)
    try {
      await onSend(text.trim(), attachment || undefined)
      setText('')
      setAttachment(null)
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleEmojiSelect = (emoji: { native: string }) => {
    setText((prev) => prev + emoji.native)
    setShowEmoji(false)
    textareaRef.current?.focus()
  }

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>, type: 'image' | 'document') => {
      const file = e.target.files?.[0]
      if (!file) return

      const attachment: Attachment = { type, file }

      if (type === 'image') {
        const reader = new FileReader()
        reader.onload = () => {
          attachment.preview = reader.result as string
          setAttachment(attachment)
        }
        reader.readAsDataURL(file)
      } else {
        setAttachment(attachment)
      }

      // Reset input
      e.target.value = ''
    },
    []
  )

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data)
        }
      }

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        const audioFile = new File([audioBlob], 'audio.webm', { type: 'audio/webm' })
        setAttachment({ type: 'audio', file: audioFile })
        stream.getTracks().forEach((track) => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
      setRecordingTime(0)

      recordingIntervalRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1)
      }, 1000)
    } catch (err) {
      console.error('Failed to start recording:', err)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current)
      }
    }
  }

  const cancelRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      setAttachment(null)
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current)
      }
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const removeAttachment = () => {
    setAttachment(null)
  }

  return (
    <div className="space-y-2">
      {/* Attachment preview */}
      {attachment && (
        <div className="flex items-center gap-2 rounded-lg bg-muted p-2">
          {attachment.type === 'image' && attachment.preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={attachment.preview}
              alt="Preview"
              className="h-16 w-16 rounded object-cover"
            />
          ) : attachment.type === 'audio' ? (
            <div className="flex items-center gap-2 text-sm">
              <Mic className="h-5 w-5 text-state-audio" />
              <span>Audio gravado</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm">
              <FileText className="h-5 w-5 text-state-document" />
              <span className="max-w-[200px] truncate">{attachment.file.name}</span>
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto h-6 w-6"
            onClick={removeAttachment}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Recording indicator */}
      {isRecording && (
        <div className="flex items-center gap-3 rounded-lg bg-state-recording p-2">
          <div className="h-3 w-3 animate-pulse rounded-full bg-state-recording-dot" />
          <span className="text-sm font-medium text-state-recording-foreground">
            Gravando {formatTime(recordingTime)}
          </span>
          <div className="ml-auto flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-state-recording-foreground hover:bg-state-recording-hover"
              onClick={cancelRecording}
            >
              Cancelar
            </Button>
            <Button size="sm" className="h-8 bg-state-recording-button hover:bg-state-recording-button-hover" onClick={stopRecording}>
              <StopCircle className="mr-1 h-4 w-4" />
              Parar
            </Button>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="flex items-end gap-2">
        {/* Emoji picker */}
        <Popover open={showEmoji} onOpenChange={setShowEmoji}>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 shrink-0"
              disabled={disabled || isRecording}
            >
              <Smile className="h-5 w-5 text-muted-foreground" />
            </Button>
          </PopoverTrigger>
          <PopoverContent side="top" align="start" className="w-auto border-none p-0 shadow-xl">
            <Picker
              data={data}
              onEmojiSelect={handleEmojiSelect}
              theme="light"
              locale="pt"
              previewPosition="none"
              skinTonePosition="none"
            />
          </PopoverContent>
        </Popover>

        {/* Attachment menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 shrink-0"
              disabled={disabled || isRecording}
            >
              <Paperclip className="h-5 w-5 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuItem onClick={() => imageInputRef.current?.click()}>
              <ImageIcon className="mr-2 h-4 w-4" />
              Imagem
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => fileInputRef.current?.click()}>
              <FileText className="mr-2 h-4 w-4" />
              Documento
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Hidden file inputs */}
        <input
          ref={imageInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => handleFileSelect(e, 'image')}
        />
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.doc,.docx,.xls,.xlsx,.txt"
          className="hidden"
          onChange={(e) => handleFileSelect(e, 'document')}
        />

        {/* Text input */}
        <Textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || 'Digite sua mensagem...'}
          className={cn(
            'max-h-[120px] min-h-[44px] flex-1 resize-none',
            isRecording && 'opacity-50'
          )}
          rows={1}
          disabled={disabled || isRecording}
        />

        {/* Audio or Send button */}
        {text.trim() || attachment ? (
          <Button
            onClick={handleSend}
            disabled={sending || disabled || isRecording}
            className="h-10 w-10 shrink-0 bg-state-ai-button p-0 hover:bg-state-ai-button-hover"
          >
            {sending ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
          </Button>
        ) : (
          <Button
            variant="ghost"
            size="icon"
            className="h-10 w-10 shrink-0"
            disabled={disabled}
            onClick={isRecording ? stopRecording : startRecording}
          >
            <Mic
              className={cn('h-5 w-5', isRecording ? 'text-state-recording-dot' : 'text-muted-foreground')}
            />
          </Button>
        )}
      </div>
    </div>
  )
}
