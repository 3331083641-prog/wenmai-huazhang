export default function Footer() {
  return (
    <footer className="py-8 border-t border-border-red/10 mt-auto bg-paper">
      <div className="max-w-7xl mx-auto px-6 text-center text-ink/60 text-sm">
        <p className="font-serif text-primary mb-2 text-lg">纹脉华章</p>
        <p>让传统文化从“被观看”走向“被共创”</p>
        <div className="mt-4 flex items-center justify-center gap-4 text-xs opacity-80">
          <span>Qwen Image 3.0 · 本地 Qwen3-VL</span>
          <span>|</span>
          <span>浏览器本地记录</span>
          <span>|</span>
          <span>文创效果预览</span>
        </div>
        <p className="mt-4 text-xs">© 2026 纹脉华章项目团队</p>
      </div>
    </footer>
  );
}
