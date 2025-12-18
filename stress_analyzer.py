from textblob import TextBlob
import re

STRESS_KEYWORDS = {
    'high_stress': [
        'overwhelmed', 'exhausted', 'burnout', 'panic', 'anxiety', 'stressed',
        'deadline', 'impossible', 'cant cope', 'too much', 'failing', 'desperate',
        'hopeless', 'drowning', 'breaking down', 'crying', 'depressed', 'suicide',
        'give up', 'quit', 'frustrated', 'angry', 'furious', 'hate', 'terrible'
    ],
    'medium_stress': [
        'worried', 'concerned', 'nervous', 'tense', 'pressure', 'busy', 'hectic',
        'challenging', 'difficult', 'struggling', 'tired', 'exhausting', 'hard',
        'confused', 'uncertain', 'anxious', 'upset', 'annoyed', 'irritated'
    ],
    'low_stress': [
        'calm', 'relaxed', 'peaceful', 'happy', 'content', 'satisfied', 'good',
        'great', 'wonderful', 'excellent', 'amazing', 'fine', 'okay', 'chill',
        'easy', 'manageable', 'confident', 'hopeful', 'excited', 'motivated'
    ]
}

ACADEMIC_STRESSORS = [
    'exam', 'test', 'assignment', 'homework', 'project', 'deadline', 'grade',
    'gpa', 'study', 'class', 'lecture', 'presentation', 'thesis', 'dissertation',
    'paper', 'quiz', 'midterm', 'final', 'submission', 'professor', 'teacher'
]

def analyze_stress(text):
    if not text or len(text.strip()) == 0:
        return {
            'stress_score': 50,
            'mood_score': 50,
            'polarity': 0,
            'subjectivity': 0.5,
            'analysis': 'No text provided for analysis'
        }
    
    text_lower = text.lower()
    blob = TextBlob(text)
    
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity
    
    high_stress_count = sum(1 for word in STRESS_KEYWORDS['high_stress'] if word in text_lower)
    medium_stress_count = sum(1 for word in STRESS_KEYWORDS['medium_stress'] if word in text_lower)
    low_stress_count = sum(1 for word in STRESS_KEYWORDS['low_stress'] if word in text_lower)
    
    academic_stressor_count = sum(1 for word in ACADEMIC_STRESSORS if word in text_lower)
    
    base_stress = 50
    
    base_stress += high_stress_count * 15
    base_stress += medium_stress_count * 8
    base_stress -= low_stress_count * 10
    
    base_stress += academic_stressor_count * 5
    
    sentiment_adjustment = -polarity * 20
    base_stress += sentiment_adjustment
    
    numbers = re.findall(r'\b(\d+)\s*(?:assignments?|exams?|tests?|projects?|deadlines?)', text_lower)
    if numbers:
        task_count = sum(int(n) for n in numbers if int(n) < 20)
        base_stress += task_count * 5
    
    stress_score = max(0, min(100, int(base_stress)))
    
    mood_score = int(100 - stress_score * 0.7 + polarity * 30)
    mood_score = max(0, min(100, mood_score))
    
    if stress_score >= 80:
        analysis = "High stress detected. Consider taking a break and seeking support."
    elif stress_score >= 60:
        analysis = "Moderate stress levels. Try some relaxation techniques."
    elif stress_score >= 40:
        analysis = "Normal stress levels. Keep maintaining a healthy balance."
    else:
        analysis = "Low stress. Great job managing your wellbeing!"
    
    return {
        'stress_score': stress_score,
        'mood_score': mood_score,
        'polarity': round(polarity, 3),
        'subjectivity': round(subjectivity, 3),
        'analysis': analysis,
        'is_high_risk': stress_score >= 85 or any(word in text_lower for word in ['suicide', 'hopeless', 'give up', 'end it'])
    }

def get_mood_emoji(stress_score):
    if stress_score >= 80:
        return '😰'
    elif stress_score >= 60:
        return '😟'
    elif stress_score >= 40:
        return '😐'
    elif stress_score >= 20:
        return '🙂'
    else:
        return '😊'
