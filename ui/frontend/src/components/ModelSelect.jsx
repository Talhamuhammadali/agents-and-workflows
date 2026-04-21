import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

export default function ModelSelect({ models, value, onChange, disabled }) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState(null);
  const rootRef = useRef(null);
  const menuRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e) {
      if (rootRef.current?.contains(e.target)) return;
      if (menuRef.current?.contains(e.target)) return;
      setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  // Anchor the menu to the trigger via fixed-position coords so ancestor
  // `overflow: hidden` can't clip it.
  function openMenu() {
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) {
      setCoords({
        left: rect.left,
        bottom: window.innerHeight - rect.top + 4,
        minWidth: rect.width,
      });
    }
    setOpen((v) => !v);
  }

  if (!models?.length) return null;

  return (
    <div className="model-select" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="model-select-trigger"
        onClick={openMenu}
        disabled={disabled}
        title="Model"
      >
        <span className="model-select-value">{value || "Model"}</span>
        <ChevronDown size={12} />
      </button>
      {open && coords && (
        <ul
          ref={menuRef}
          className="model-select-menu"
          role="listbox"
          style={{ left: coords.left, bottom: coords.bottom, minWidth: coords.minWidth }}
        >
          {models.map((m) => (
            <li
              key={m}
              role="option"
              aria-selected={m === value}
              className={`model-select-option ${m === value ? "selected" : ""}`}
              onClick={() => {
                onChange?.(m);
                setOpen(false);
              }}
            >
              {m}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
