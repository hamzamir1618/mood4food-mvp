import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

const ToastContext = createContext(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const timer = useRef(null);

  const show = useCallback((text, kind = 'info', ms = 2600) => {
    if (!text) return;
    clearTimeout(timer.current);
    setToast({ text, kind, at: Date.now() });
    timer.current = setTimeout(() => setToast(null), ms);
  }, []);

  useEffect(() => () => clearTimeout(timer.current), []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      {toast && (
        <div className="toast-wrap" aria-live="polite">
          <div key={toast.at} className={`toast${toast.kind === 'error' ? ' is-error' : ''}`}>
            {toast.text}
          </div>
        </div>
      )}
    </ToastContext.Provider>
  );
}
