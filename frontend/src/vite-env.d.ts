/// <reference types="vite/client" />

declare module 'lucide-react' {
  import type { ComponentType, SVGProps } from 'react'
  type IconProps = SVGProps<SVGSVGElement> & { size?: number | string; strokeWidth?: number | string }
  export const AlertCircle: ComponentType<IconProps>
  export const ArrowUpRight: ComponentType<IconProps>
  export const BarChart3: ComponentType<IconProps>
  export const Bot: ComponentType<IconProps>
  export const Check: ComponentType<IconProps>
  export const ChevronDown: ComponentType<IconProps>
  export const CircleHelp: ComponentType<IconProps>
  export const FileText: ComponentType<IconProps>
  export const Gauge: ComponentType<IconProps>
  export const Layers3: ComponentType<IconProps>
  export const LoaderCircle: ComponentType<IconProps>
  export const MessageSquare: ComponentType<IconProps>
  export const Paperclip: ComponentType<IconProps>
  export const PanelRight: ComponentType<IconProps>
  export const RefreshCw: ComponentType<IconProps>
  export const Send: ComponentType<IconProps>
  export const ShieldCheck: ComponentType<IconProps>
  export const Sparkles: ComponentType<IconProps>
  export const UploadCloud: ComponentType<IconProps>
  export const X: ComponentType<IconProps>
  export const Zap: ComponentType<IconProps>
}

declare module '*.css'
