# app/services/margin_service.py

from openai import OpenAI
from flask import current_app
from app.extensions import db
from app.models import MarginSuggestion, Category, TempProduct
import json
from datetime import datetime

class EnhancedMarginService:
    def __init__(self):
        self.client = OpenAI(api_key=current_app.config['OPENAI_API_KEY'])
        self.logger = current_app.logger

    def get_margin_suggestions(self, invoice_id, location, area_type=None):
        """Get AI-suggested margins based on location and market data"""
        try:
            # Get unique categories from temp products
            categories = db.session.query(TempProduct.category_name).filter_by(
                invoice_id=invoice_id
            ).distinct().all()
            category_names = [cat[0] for cat in categories]

            if not category_names:
                raise ValueError(f"No categories found for invoice {invoice_id}")

            # Get historical margin data
            historical_data = self._get_historical_margins(category_names)

            # Get market insights
            market_data = self._get_market_insights(location, area_type)

            # Prepare prompt with all available data
            prompt = self._prepare_margin_prompt(
                category_names,
                location,
                area_type,
                historical_data,
                market_data
            )

            # Get AI suggestions
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[{
                    "role": "system",
                    "content": """You are a retail pricing expert specializing in beauty supply stores.
                    Analyze the provided data and suggest optimal profit margins."""
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            # Process and validate response
            content = response.choices[0].message.content.strip()
            suggestions = json.loads(content)

            # Validate and store suggestions
            validated_suggestions = self._process_suggestions(
                invoice_id,
                suggestions,
                location,
                area_type
            )

            return validated_suggestions

        except Exception as e:
            self.logger.error(f"Error getting margin suggestions: {str(e)}")
            raise

    def _get_historical_margins(self, categories):
        """Get historical margin data for categories"""
        historical_data = {}
        for category in categories:
            cat_data = self._analyze_category_history(category)
            if cat_data:
                historical_data[category] = cat_data
        return historical_data

    def _analyze_category_history(self, category):
        """Analyze historical performance of a category"""
        try:
            # Get category details
            category_obj = Category.query.filter_by(name=category).first()
            if not category_obj:
                return None

            # Get recent margin suggestions
            recent_suggestions = MarginSuggestion.query.filter_by(
                category_name=category
            ).order_by(
                MarginSuggestion.created_at.desc()
            ).limit(10).all()

            return {
                'default_margin': category_obj.default_margin,
                'recent_suggestions': [
                    {
                        'margin': s.suggested_margin,
                        'location': s.location,
                        'date': s.created_at.isoformat()
                    } for s in recent_suggestions
                ]
            }

        except Exception as e:
            self.logger.error(f"Error analyzing category history: {str(e)}")
            return None

    def _get_market_insights(self, location, area_type):
        """Get market insights for location"""
        try:
            # Call GPT-4 for market analysis
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[{
                    "role": "system",
                    "content": """You are a market research expert. Analyze the given location
                    and provide insights about the market conditions for a beauty supply store."""
                }, {
                    "role": "user",
                    "content": f"""Analyze market conditions for:
                    Location: {location}
                    Area Type: {area_type or 'Not specified'}
                    
                    Provide insights about:
                    1. Competition level
                    2. Local purchasing power
                    3. Market saturation
                    4. Growth potential
                    5. Consumer demographics
                    
                    Return as structured JSON."""
                }],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            insights = json.loads(response.choices[0].message.content)
            return insights

        except Exception as e:
            self.logger.error(f"Error getting market insights: {str(e)}")
            return None

    def _prepare_margin_prompt(self, categories, location, area_type, historical_data, market_data):
        """Prepare detailed prompt for AI"""
        prompt = f"""Based on the following data, suggest optimal profit margins for each category:

Categories to analyze: {json.dumps(categories)}

Location Information:
- Location: {location}
- Area Type: {area_type or 'Not specified'}
- Market Analysis: {json.dumps(market_data, indent=2)}

Historical Data:
{json.dumps(historical_data, indent=2)}

Requirements:
1. Suggest margins for each category (as percentages)
2. Provide reasoning for each suggestion
3. Consider local market conditions
4. Account for category-specific factors
5. Balance competitiveness with profitability

Return response in this exact JSON format:
{{
    "margins": {{
        "category_name": {{
            "suggested_margin": float,
            "reasoning": [string],
            "confidence": float,
            "risk_level": string
        }}
    }},
    "market_summary": {{
        "overall_assessment": string,
        "key_factors": [string],
        "recommendations": [string]
    }}
}}"""
        return prompt

    def _process_suggestions(self, invoice_id, suggestions, location, area_type):
        """Process and validate AI suggestions"""
        try:
            # Validate suggestions format
            if not isinstance(suggestions, dict) or 'margins' not in suggestions:
                raise ValueError("Invalid suggestion format")

            processed_suggestions = []
            for category, data in suggestions['margins'].items():
                # Validate margin value
                margin = float(data['suggested_margin'])
                if margin < 0 or margin > 100:
                    self.logger.warning(f"Invalid margin {margin} for {category}")
                    continue

                # Create suggestion record
                suggestion = MarginSuggestion(
                    invoice_id=invoice_id,
                    category_name=category,
                    suggested_margin=margin,
                    location=location,
                    area_type=area_type,
                    insights={
                        'reasoning': data.get('reasoning', []),
                        'confidence': data.get('confidence', 0.0),
                        'risk_level': data.get('risk_level', 'medium')
                    }
                )
                db.session.add(suggestion)
                processed_suggestions.append(suggestion)

            # Add market summary
            if 'market_summary' in suggestions:
                market_suggestion = MarginSuggestion(
                    invoice_id=invoice_id,
                    category_name='_market_summary',
                    location=location,
                    area_type=area_type,
                    insights=suggestions['market_summary']
                )
                db.session.add(market_suggestion)

            db.session.commit()

            return {
                'status': 'success',
                'suggestions': [
                    {
                        'category': s.category_name,
                        'margin': s.suggested_margin,
                        'insights': s.insights
                    } for s in processed_suggestions
                ],
                'market_summary': suggestions.get('market_summary', {})
            }

        except Exception as e:
            self.logger.error(f"Error processing suggestions: {str(e)}")
            db.session.rollback()
            raise

    def update_category_margins(self, invoice_id, margins):
        """Update margins for categories"""
        try:
            updates = []
            for category, margin in margins.items():
                # Validate margin
                if not isinstance(margin, (int, float)) or margin < 0 or margin > 100:
                    raise ValueError(f"Invalid margin value for {category}: {margin}")

                # Update category default margin
                category_obj = Category.query.filter_by(name=category).first()
                if category_obj:
                    category_obj.default_margin = margin
                    updates.append(category_obj)

            if updates:
                db.session.bulk_save_objects(updates)
                db.session.commit()

            return {
                'status': 'success',
                'updated_categories': len(updates)
            }

        except Exception as e:
            self.logger.error(f"Error updating category margins: {str(e)}")
            db.session.rollback()
            raise

    def get_margin_history(self, category_name, limit=10):
        """Get margin history for a category"""
        try:
            history = MarginSuggestion.query.filter_by(
                category_name=category_name
            ).order_by(
                MarginSuggestion.created_at.desc()
            ).limit(limit).all()

            return {
                'category': category_name,
                'history': [
                    {
                        'margin': h.suggested_margin,
                        'location': h.location,
                        'insights': h.insights,
                        'date': h.created_at.isoformat()
                    } for h in history
                ]
            }

        except Exception as e:
            self.logger.error(f"Error getting margin history: {str(e)}")
            raise

    def analyze_margin_impact(self, invoice_id, proposed_margins):
        """Analyze impact of proposed margins"""
        try:
            # Get all products for the invoice
            products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
            
            current_totals = {
                'cost': sum(p.cost_price * p.quantity for p in products),
                'revenue': sum(p.selling_price * p.quantity if p.selling_price else 0 for p in products)
            }
            
            # Calculate proposed totals
            proposed_revenue = 0
            for product in products:
                margin = proposed_margins.get(product.category_name)
                if margin:
                    selling_price = product.cost_price * (1 + margin/100)
                    proposed_revenue += selling_price * product.quantity

            return {
                'current': {
                    'total_cost': current_totals['cost'],
                    'total_revenue': current_totals['revenue'],
                    'total_profit': current_totals['revenue'] - current_totals['cost']
                },
                'proposed': {
                    'total_cost': current_totals['cost'],
                    'total_revenue': proposed_revenue,
                    'total_profit': proposed_revenue - current_totals['cost']
                },
                'difference': {
                    'revenue': proposed_revenue - current_totals['revenue'],
                    'profit': (proposed_revenue - current_totals['cost']) - 
                             (current_totals['revenue'] - current_totals['cost'])
                }
            }

        except Exception as e:
            self.logger.error(f"Error analyzing margin impact: {str(e)}")
            raise

    def get_competitive_analysis(self, location, categories):
        """Get competitive analysis for categories in location"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[{
                    "role": "system",
                    "content": """You are a competitive analysis expert for retail stores.
                    Analyze the competitive landscape for the given categories in the specified location."""
                }, {
                    "role": "user",
                    "content": f"""Analyze competitive landscape for:
                    Location: {location}
                    Categories: {json.dumps(categories)}
                    
                    Consider:
                    1. Local competition
                    2. Price sensitivity
                    3. Market positioning
                    4. Growth opportunities
                    
                    Return structured analysis in JSON format."""
                }],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            return analysis

        except Exception as e:
            self.logger.error(f"Error getting competitive analysis: {str(e)}")
            raise