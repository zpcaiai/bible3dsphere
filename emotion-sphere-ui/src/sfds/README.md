# SFDS UI - Spiritual Formation & Discernment System

A clean, minimal, non-judgmental UI for spiritual decision support.

## Design Philosophy

**As a "spiritual mirror", not an oracle:**
- Does not claim divine authority
- Presents multiple interpretations
- Emphasizes humility and uncertainty
- Encourages community discernment
- Avoids performance pressure

## Pages

### 1. Dashboard (`Dashboard.jsx`)
- Current emotional state (stress, anxiety, peace, joy, fatigue, spiritual vitality)
- Recent decisions with source classification
- Spiritual trend chart (placeholder for future implementation)
- Daily reflection prompt
- Quick action to start new decision

**Features:**
- State indicators with color coding
- Gentle reminders based on current state
- Decision cards showing primary source
- Wellbeing score calculation

### 2. Decision Input (`DecisionInput.jsx`)
4-step guided input process:

**Step 1: Describe Situation**
- Decision title
- Category selection (career, relationship, temptation, calling, etc.)
- Detailed description (optional)
- Urgency and importance levels (1-5)

**Step 2: Select Emotions**
- Grid of emotion chips (positive, negative, neutral)
- Max 3 emotions
- Categories: joy, peace, fear, anxiety, confusion, etc.

**Step 3: State Snapshot**
- Sliders for: stress, anxiety, fatigue, spiritual dryness, emotional stability
- All 1-10 scale
- Contextual labels (e.g., "轻松" to "压力很大")

**Step 4: Review & Submit**
- Summary of all inputs
- Gentle reminder about the tool's purpose
- Submit for analysis

### 3. Discernment Result (`DiscernmentResult.jsx`)
Comprehensive analysis display with 5 tabs:

**Tab: 概览 (Overview)**
- Primary source classification (e.g., "恐惧反应")
- Confidence level and score
- Explanation with humility statement
- Risk assessment with factors
- Alternative interpretations
- Expandable disclaimer

**Tab: 动机 (Motive)**
- Visual breakdown of 5 motives
- Progress bars with percentages
- Descriptions for each motive
- Reflection on motive purity

**Tab: 原则 (Principles)**
- Related spiritual principles from Bible
- Relevance scores
- Scripture references
- Reflection question

**Tab: 果实 (Fruit)**
- Long-term fruit prediction
- Emoji + score visualization
- Explanation of prediction
- Note about God's intervention

**Tab: 下一步 (Next Steps)**
- Numbered reflection exercises
- Thought-provoking questions
- Timeline recommendation
- Link to journal

### 4. Reflection Journal (`ReflectionJournal.jsx`)
Two views:

**Entries View**
- Timeline of past entries
- Daily reflections and decision reviews
- Emotion tags
- Decision outcome tracking
- New entry button

**Prompts View**
- Curated reflection prompts
- Topics: gratitude, challenges, emotions, divine perspective
- One-click to use as journal entry title

**New Entry Screen**
- Type: daily / decision review
- Emotion selection
- Free-form writing area
- Pre-populated with selected prompt
- Gentle reminder about honesty

## Components

### Visual Components
- `sfds-card`: Elevated card with subtle shadow
- `sfds-card-gentle`: Card with gradient background
- `sfds-btn`: Primary, secondary, gentle variants
- `sfds-input`: Text input with focus states
- `sfds-select`: Styled select dropdown
- `sfds-slider`: Range input with labels
- `sfds-emotion-chip`: Selectable emotion buttons
- `sfds-badge`: Status indicators (teal, sage, warm, muted)
- `sfds-timeline`: Vertical timeline for journal entries
- `sfds-principle-card`: Bible principle display
- `sfds-reflection-box`: Highlighted reflection area
- `sfds-progress-bar`: Visual progress indicator

### Layout Components
- `sfds-page`: Page wrapper with max-width
- `sfds-container`: Full-height background container
- `sfds-nav`: Fixed bottom navigation
- `sfds-section-title`: Consistent section headers
- `sfds-empty`: Empty state placeholder

## Color Palette

```css
--sfds-bg-primary: #faf9f7;      /* Warm off-white */
--sfds-bg-secondary: #f5f3f0;  /* Light warm gray */
--sfds-bg-card: #ffffff;        /* Pure white */

--sfds-text-primary: #3d3d3d;   /* Dark gray */
--sfds-text-secondary: #6b6b6b;/* Medium gray */
--sfds-text-muted: #9a9a9a;     /* Light gray */

--sfds-accent-teal: #5a9a8f;    /* Primary - calm teal */
--sfds-accent-teal-light: #e8f4f2;
--sfds-accent-sage: #8fa872;    /* Secondary - sage green */
--sfds-accent-sage-light: #f0f5eb;
--sfds-accent-warm: #c4a77d;    /* Tertiary - warm gold */
--sfds-accent-warm-light: #faf6f0;
```

## Usage

```jsx
import { SFDSApp } from './sfds';

// As standalone app
function App() {
  return <SFDSApp />;
}

// As embedded component with close handler
function App() {
  const [showSFDS, setShowSFDS] = useState(false);
  
  return (
    <>
      <button onClick={() => setShowSFDS(true)}>
        灵性决策支持
      </button>
      {showSFDS && (
        <SFDSApp onClose={() => setShowSFDS(false)} />
      )}
    </>
  );
}
```

## Navigation

The app includes 4 bottom navigation items:
1. **首页** (Dashboard) - Overview and quick actions
2. **新决定** (New Decision) - Start decision input flow
3. **日记** (Journal) - Reflection entries
4. **历史** (History) - All past decisions

## Responsive Design

- Mobile-first design
- Max-width: 800px for larger screens
- Fixed bottom navigation
- Touch-friendly buttons (min 44px)
- Responsive grid layouts

## Accessibility

- Semantic HTML structure
- Focus states for all interactive elements
- ARIA labels where needed
- Color contrast meets WCAG standards
- Keyboard navigation support

## Future Enhancements

- [ ] Spiritual trend chart with real data
- [ ] Decision history filtering
- [ ] Integration with backend API
- [ ] Push notifications for reflection reminders
- [ ] Export journal entries
- [ ] Dark mode support
- [ ] Multi-language support
