import { useState, useRef, useCallback } from 'react';
import { useToast } from './Toast.jsx';

export default function QueryBar({ onSubmit, disabled }) {
  const [queryText, setQueryText] = useState('');
  const [audioFile, setAudioFile] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [statusText, setStatusText] = useState('');
  const [statusClass, setStatusClass] = useState('query-status');
  const [budgetWarning, setBudgetWarning] = useState(null);
  const [inputDisabled, setInputDisabled] = useState(false);
  const lastWarnedQueryRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const imageInputRef = useRef(null);
  const showToast = useToast();

  const doSubmit = useCallback((text, aFile, iFile, customLoadingMsg) => {
    setBudgetWarning(null);
    lastWarnedQueryRef.current = null;
    onSubmit(text, aFile, iFile, customLoadingMsg, {
      setStatusText,
      setStatusClass,
      setInputDisabled,
    });
    // Clear files after submit
    setAudioFile(null);
    setImageFile(null);
    if (imageInputRef.current) imageInputRef.current.value = '';
  }, [onSubmit]);

  const handleFormSubmit = useCallback((e) => {
    e.preventDefault();
    const text = queryText.trim();

    // Budget warning logic
    const budgetMatch = text.match(/(?:under|budget|max|below|for)\s*[a-z\s]*?(?:rs\.?\s*|rupees\s*)?(\d+)/i) || text.match(/(\d+)\s*(?:rs|rupees|pkr)/i);
    if (budgetMatch && !audioFile && !imageFile) {
      const parsedBudget = parseInt(budgetMatch[1], 10);
      if (parsedBudget > 0 && parsedBudget < 50 && text !== lastWarnedQueryRef.current) {
        setBudgetWarning({ budget: parsedBudget, text });
        lastWarnedQueryRef.current = text;
        return;
      }
    }

    setBudgetWarning(null);
    lastWarnedQueryRef.current = null;

    if (text || audioFile || imageFile) {
      doSubmit(text, audioFile, imageFile);
    }
  }, [queryText, audioFile, imageFile, doSubmit]);

  const handleSearchAnyway = useCallback((e) => {
    e.preventDefault();
    const text = budgetWarning?.text || queryText.trim();
    setBudgetWarning(null);
    doSubmit(text, audioFile, imageFile);
  }, [budgetWarning, queryText, audioFile, imageFile, doSubmit]);

  const handleAudioClick = useCallback(async () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        audioChunksRef.current = [];
        mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
        mediaRecorder.onstop = () => {
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const file = new File([blob], 'recording.webm', { type: 'audio/webm' });
          stream.getTracks().forEach(t => t.stop());
          setAudioFile(file);
          doSubmit('', file, null, 'Listening...');
        };
        mediaRecorder.start();
        mediaRecorderRef.current = mediaRecorder;
      } catch (err) {
        console.error("Microphone error:", err);
        showToast("Could not access microphone.", "error");
      }
    }
  }, [doSubmit, showToast]);

  const handleImageClick = useCallback(() => {
    imageInputRef.current?.click();
  }, []);

  const handleImageChange = useCallback((e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      doSubmit('', null, file, 'Analyzing image...');
    }
  }, [doSubmit]);

  const isRecording = mediaRecorderRef.current?.state === 'recording';

  return (
    <div className="query-bar-wrapper">
      <div className="query-bar" id="query-bar">
        <form id="query-form" autoComplete="off" onSubmit={handleFormSubmit}>
          <div className="query-input-row">
            <span className="query-icon">🔍</span>
            <input
              type="text"
              id="query-input"
              className="query-input"
              placeholder='Try: "spicy food under 500 rupees, no dairy"'
              aria-label="Describe what you want to eat"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              disabled={inputDisabled}
            />
            <button
              type="button"
              className="upload-btn"
              id="audio-btn"
              title="Attach audio"
              onClick={handleAudioClick}
              style={isRecording ? { color: '#EF4444' } : {}}
            >
              {isRecording ? '⏹' : '🎤'}
            </button>
            <button type="button" className="upload-btn" id="image-btn" title="Attach image" onClick={handleImageClick}>📷</button>
            <input type="file" id="image-file" accept=".jpg,.jpeg,.png,.webp" hidden ref={imageInputRef} onChange={handleImageChange} />
            <button type="submit" className="query-submit" id="query-submit" disabled={inputDisabled}>
              Find Food
            </button>
          </div>
          <div className="file-chips" id="file-chips">
            {audioFile && (
              <div className="file-chip">🎤 {audioFile.name}
                <button type="button" className="chip-remove" onClick={() => setAudioFile(null)} aria-label={`Remove audio file ${audioFile.name}`}>✕</button>
              </div>
            )}
            {imageFile && (
              <div className="file-chip">📷 {imageFile.name}
                <button type="button" className="chip-remove" onClick={() => { setImageFile(null); if (imageInputRef.current) imageInputRef.current.value = ''; }} aria-label={`Remove image file ${imageFile.name}`}>✕</button>
              </div>
            )}
          </div>
        </form>
        {budgetWarning && (
          <div id="budget-warning" className="budget-warning">
            ⚠️ That budget (Rs. {budgetWarning.budget}) is very low — you may not get results.{' '}
            <a href="#" id="search-anyway-btn" style={{ color: 'var(--accent-budget)', textDecoration: 'underline', marginLeft: 8 }} onClick={handleSearchAnyway}>
              Search anyway
            </a>
          </div>
        )}
        <div className={statusClass} id="query-status">{statusText}</div>
      </div>
    </div>
  );
}
