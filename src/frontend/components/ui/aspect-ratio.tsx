import * as React from "react"

type AspectRatioProps = React.HTMLAttributes<HTMLDivElement> & {
  ratio?: number // width / height
}

export function AspectRatio({ ratio = 16 / 9, className = "", children, style, ...props }: AspectRatioProps) {
  const paddingTop = `${(1 / ratio) * 100}%`
  return (
    <div className={`relative w-full ${className}`} style={{ ...style, paddingTop }} {...props}>
      <div className="absolute inset-0">{children}</div>
    </div>
  )
}



