export class ScrollManager {
  private container: HTMLElement;
  private isScrolledToBottom: boolean = true;
  private scrollThreshold: number = 100; // pixels from bottom

  constructor(container: HTMLElement) {
    this.container = container;
    this.attachScrollListener();
  }

  private attachScrollListener() {
    this.container.addEventListener("scroll", () => {
      const { scrollTop, scrollHeight, clientHeight } = this.container;
      this.isScrolledToBottom =
        scrollHeight - (scrollTop + clientHeight) <= this.scrollThreshold;
    });
  }

  public immediateScrollToBottom() {
    this.container.scrollTop = this.container.scrollHeight;
    this.isScrolledToBottom = true;
  }

  public handleNewContent() {
    if (this.isScrolledToBottom) {
      // Use requestAnimationFrame to ensure DOM has updated
      requestAnimationFrame(() => {
        this.container.scrollTop = this.container.scrollHeight;
      });
    }
  }

  public destroy() {
    // Clean up event listeners if needed
    this.container.removeEventListener("scroll", this.attachScrollListener);
  }
}
