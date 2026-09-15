import { motion } from 'framer-motion';
import LogoMark from './LogoMark.jsx';

export default function Header({ onRefresh }) {
  return (
    <header className="hero">
      <div className="hero-inner">
        <motion.div
          className="hero-brand"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        >
          <LogoMark size={44} className="hero-logo-mark" />
          <div className="hero-text">
            <h1>Mood4Food</h1>
            <p>Your Smart Food Recommender</p>
          </div>
        </motion.div>
        <button
          className="hero-refresh"
          id="refresh-btn"
          title="Refresh recommendations"
          aria-label="Refresh recommendations"
          onClick={onRefresh}
        >
          🔄
        </button>
      </div>
    </header>
  );
}
