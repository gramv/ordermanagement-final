import os
import requests
from flask import current_app

def get_demographics(location):
    """Get demographic data for a location using Census API"""
    try:
        # In a real app, use Census API to get demographics
        # For demo, return mock data
        return {
            'median_income': 65000,
            'population': 50000,
            'median_age': 35,
            'households': 20000
        }
    except Exception as e:
        current_app.logger.error(f"Error getting demographics: {str(e)}")
        return {
            'median_income': 50000,  # Default fallback
            'population': 25000,
            'median_age': 30,
            'households': 10000
        }

def analyze_competition(location):
    """Analyze competition in the area using Google Places API"""
    try:
        # In a real app, use Google Places API to get nearby businesses
        # For demo, return mock data
        return {
            'level': 'medium',  # high, medium, low
            'nearby_stores': 5,
            'avg_rating': 4.2,
            'price_level': 2  # 1-4 scale
        }
    except Exception as e:
        current_app.logger.error(f"Error analyzing competition: {str(e)}")
        return {
            'level': 'medium',  # Default fallback
            'nearby_stores': 3,
            'avg_rating': 4.0,
            'price_level': 2
        }

def get_market_insights(location, area_type):
    """Get market insights combining demographics and competition"""
    demographics = get_demographics(location)
    competition = analyze_competition(location)
    
    insights = {
        'demographics': demographics,
        'competition': competition,
        'recommendations': []
    }
    
    # Add recommendations based on analysis
    if demographics['median_income'] > 75000:
        insights['recommendations'].append(
            "Higher income area - consider premium pricing for luxury items"
        )
    
    if competition['level'] == 'high':
        insights['recommendations'].append(
            "High competition - consider competitive pricing and focus on service quality"
        )
    elif competition['level'] == 'low':
        insights['recommendations'].append(
            "Low competition - opportunity for premium pricing in underserved market"
        )
    
    if area_type == 'urban':
        insights['recommendations'].append(
            "Urban location - focus on convenience and quick service"
        )
    elif area_type == 'suburban':
        insights['recommendations'].append(
            "Suburban location - emphasize family-friendly offerings"
        )
    elif area_type == 'rural':
        insights['recommendations'].append(
            "Rural location - consider broader inventory and essential items"
        )
    
    return insights
