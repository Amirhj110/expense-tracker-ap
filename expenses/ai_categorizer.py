import re
from .models import Category

class ExpenseCategorizer:
    """Simple AI that categorizes expenses based on keywords"""
    
    # Keywords for each category
    KEYWORDS = {
        'Food & Dining': ['restaurant', 'cafe', 'food', 'lunch', 'dinner', 'breakfast', 
                         'pizza', 'burger', 'groceries', 'supermarket', 'starbucks', 
                         'coffee', 'mcdonalds', 'kfc', 'subway'],
        
        'Transportation': ['uber', 'lyft', 'taxi', 'bus', 'train', 'metro', 'gas', 
                          'fuel', 'parking', 'car', 'bike'],
        
        'Shopping': ['amazon', 'walmart', 'target', 'mall', 'clothes', 'shoes', 
                    'electronics', 'store', 'best buy', 'costco'],
        
        'Entertainment': ['movie', 'cinema', 'netflix', 'spotify', 'concert', 'game', 
                         'theater', 'music', 'hulu', 'disney'],
        
        'Bills & Utilities': ['electric', 'water', 'gas bill', 'internet', 'phone bill', 
                             'rent', 'mortgage', 'insurance', 'wifi'],
        
        'Healthcare': ['doctor', 'hospital', 'medicine', 'pharmacy', 'clinic', 'dental', 
                      'cvs', 'walgreens', 'health'],
        
        'Education': ['school', 'university', 'college', 'course', 'book', 'tuition', 
                     'udemy', 'coursera', 'class'],
        
        'Travel': ['flight', 'hotel', 'airbnb', 'travel', 'vacation', 'airline', 
                  'booking', 'trip', 'tour']
    }
    
    @classmethod
    def categorize(cls, description):
        """Suggest category based on expense description"""
        description_lower = description.lower()
        
        # Count keyword matches for each category
        matches = {}
        for category, keywords in cls.KEYWORDS.items():
            match_count = sum(1 for keyword in keywords if keyword in description_lower)
            if match_count > 0:
                matches[category] = match_count
        
        # Find category with most matches
        if matches:
            best_category = max(matches, key=matches.get)
            try:
                return Category.objects.get(name=best_category)
            except Category.DoesNotExist:
                return Category.objects.get(name='Other')
        
        # Default to 'Other' if no matches
        return Category.objects.get(name='Other')
    
    @classmethod
    def suggest_categories(cls, description):
        """Return top category suggestions with confidence scores"""
        description_lower = description.lower()
        suggestions = []
        
        for category, keywords in cls.KEYWORDS.items():
            match_count = sum(1 for keyword in keywords if keyword in description_lower)
            if match_count > 0:
                confidence = min(match_count * 20, 100)  # Simple confidence calculation
                suggestions.append({
                    'category': category,
                    'confidence': confidence
                })
        
        # Sort by confidence and return top 3
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:3]
    



    