import { useEffect, useState, type RefObject } from "react";

export function useVisualViewportHeight(): number | null {
  const [height, setHeight] = useState<number | null>(null);

  useEffect(() => {
    const sync = () => {
      const vv = window.visualViewport;
      setHeight(vv?.height ?? window.innerHeight);
    };

    sync();
    window.visualViewport?.addEventListener("resize", sync);
    window.visualViewport?.addEventListener("scroll", sync);
    window.addEventListener("resize", sync);

    return () => {
      window.visualViewport?.removeEventListener("resize", sync);
      window.visualViewport?.removeEventListener("scroll", sync);
      window.removeEventListener("resize", sync);
    };
  }, []);

  return height;
}

/** Distance the virtual keyboard overlaps the layout viewport bottom. */
export function useVisualViewportKeyboardOffset(): number {
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const sync = () => {
      const vv = window.visualViewport;
      if (!vv) {
        setOffset(0);
        return;
      }
      setOffset(Math.max(0, window.innerHeight - vv.height - vv.offsetTop));
    };

    sync();
    window.visualViewport?.addEventListener("resize", sync);
    window.visualViewport?.addEventListener("scroll", sync);
    window.addEventListener("resize", sync);

    return () => {
      window.visualViewport?.removeEventListener("resize", sync);
      window.visualViewport?.removeEventListener("scroll", sync);
      window.removeEventListener("resize", sync);
    };
  }, []);

  return offset;
}

export function useElementHeight<T extends HTMLElement>(
  ref: RefObject<T | null>,
  deps: unknown[] = [],
): number {
  const [height, setHeight] = useState(0);

  useEffect(() => {
    const node = ref.current;
    if (!node) {
      return;
    }

    const measure = () => {
      setHeight(node.getBoundingClientRect().height);
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, [ref, ...deps]);

  return height;
}
