from datetime import datetime
from app.models.circle import Circle
from app.models.enums import CircleFrequency

def calculate_current_cycle(circle: Circle) -> int:
    """
    Calculate the current cycle number for a circle based on its start date and frequency.
    Cycle starts at 1.
    """
    if not circle.cycle_start_date:
        return 0 # Or 1 depending on logic, but 0 means not started
    
    now = datetime.now()
    start_date = circle.cycle_start_date
    
    # Calculate difference
    diff = now - start_date
    
    if circle.frequency == CircleFrequency.WEEKLY:
        # Cycles are every 7 days
        days_passed = diff.days
        cycle_number = (days_passed // 7) + 1
        
    elif circle.frequency == CircleFrequency.BIWEEKLY:
        # Cycles are every 14 days
        days_passed = diff.days
        cycle_number = (days_passed // 14) + 1
        
    elif circle.frequency == CircleFrequency.MONTHLY:
        # Simple month difference approach
        # (This can be complex with days of month, but standard approach is diff in months)
        months_passed = (now.year - start_date.year) * 12 + (now.month - start_date.month)
        
        # Check if the day of month has passed
        # If today is 5th and start was 10th, and we are next month, we might still be in cycle 1?
        # Let's keep it simple: Cycle changes on the same day next month
        if now.day < start_date.day:
            months_passed -= 1
            
        cycle_number = months_passed + 1
        
    else:
        # Default fallback
        cycle_number = 1
        
    return max(1, cycle_number)
