from flask import Flask, render_template, request, jsonify
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# Load Excel sheets
df_food = pd.read_excel("Modified_Nutrition_Data_No_Beverages.xlsx")
df_bev = pd.read_excel("Beverages_Nutrition_Data.xlsx")

# Normalize column names
for df in [df_food, df_bev]:
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    df['food_name'] = df['food_name'].str.lower()

# Chatbot state management
user_sessions = {}

#  Core Functions  
def search_excel(user_input):
    food = user_input.strip().lower()
    results = []

    for df in [df_food, df_bev]:
        matches = df[df['food_name'].str.contains(food)]
        for _, row in matches.iterrows():
            result = {
                'food_name': row['food_name'].title(),
                'energy': row['energy_kcal'],
                'carbs': row['carb_g'],
                'protein': row['protein_g'],
                'fat': row['fat_g'],
                'fibre': row['fibre_g']
            }
            results.append(result)
    return results if results else None

def compare_foods(food1, food2):
    food1 = food1.lower()
    food2 = food2.lower()
    combined_df = pd.concat([df_food, df_bev], ignore_index=True)

    row1 = combined_df[combined_df['food_name'].str.contains(food1)]
    row2 = combined_df[combined_df['food_name'].str.contains(food2)]

    if row1.empty or row2.empty:
        return None

    row1 = row1.iloc[0]
    row2 = row2.iloc[0]

    comparison = {
        'food1': {
            'name': row1['food_name'].title(),
            'energy': row1['energy_kcal'],
            'carbs': row1['carb_g'],
            'protein': row1['protein_g'],
            'fat': row1['fat_g'],
            'fibre': row1['fibre_g']
        },
        'food2': {
            'name': row2['food_name'].title(),
            'energy': row2['energy_kcal'],
            'carbs': row2['carb_g'],
            'protein': row2['protein_g'],
            'fat': row2['fat_g'],
            'fibre': row2['fibre_g']
        }
    }
    
    if row1['protein_g'] > row2['protein_g']:
        comparison['key'] = f"✅ {row1['food_name'].title()} is richer in protein."
    elif row2['protein_g'] > row1['protein_g']:
        comparison['key'] = f"✅ {row2['food_name'].title()} is richer in protein."
    else:
        comparison['key'] = "ℹ️ Both have similar protein levels."
    
    return comparison

def top_nutrient_items(category, nutrient):
    df = df_food if category == "food" else df_bev

    if nutrient == "low fat":
        top = df.nsmallest(5, "fat_g")
    elif nutrient == "high protein":
        top = df.nlargest(5, "protein_g")
    elif nutrient == "high fibre":
        top = df.nlargest(5, "fibre_g")
    else:
        return None

    results = []
    for _, row in top.iterrows():
        results.append({
            'food_name': row['food_name'].title(),
            'energy': row['energy_kcal'],
            'fat': row['fat_g'],
            'protein': row['protein_g'],
            'fibre': row['fibre_g']
        })
    
    return {
        'category': category,
        'nutrient': nutrient,
        'results': results
    }

#  Conversation Handlers 
def handle_general_conversation(user_input, session_id):
    user_input = user_input.lower()

    if any(greet in user_input for greet in ["hi", "hello", "hey"]):
        return {
            'type': 'greeting',
            'response': "👋 Hello! I'm NutriBot. How may I assist you today? Type MENU to see all available commands."
        }
    
    if "help" in user_input or "what can you do" in user_input:
        return {
            'type': 'help',
            'response': (
                "😊 I can help you with:\n"
                "1. 🍽️ Nutritional info of any food or drink\n"
                "2. ⚖️ Compare two foods\n"
                "3. 🔍 Suggest top low-fat, high-protein, or fiber-rich items\n"
                "Type one of these to get started!"
            )
        }
    
    if "thank" in user_input:
        return {
            'type': 'thanks',
            'response': "You're most welcome! 💚"
        }
    
    if any(word in user_input for word in ["compare", "comparison","2"]):
        user_sessions[session_id] = {'mode': 'compare', 'step': 1}
        return {
            'type': 'compare_init',
            'response': "Let's compare two foods! Please enter the first food item:"
        }
    
    if any(word in user_input for word in ["top", "suggest", "recommend","3"]):
        user_sessions[session_id] = {'mode': 'top', 'step': 1}
        return {
            'type': 'top_init',
            'response': "Great! First, should I search in 'food' or 'beverages'?"
        }
    
    if any(word in user_input for word in ["1", "nutrition", "info"]):
        return {
            'type': 'nutrition_info',
            'response': "Sure! Please enter the name of the food or drink you want nutritional info for:"
        }


    if "menu" in user_input or "option" in user_input:
        return {
            'type': 'menu',
            'response': show_main_menu()
        }
    
    return None

def show_main_menu():
    return (
        "\nWhat would you like to do?\n"
        "1️⃣ Know nutrition info\n"
        "2️⃣ Compare two food items\n"
        "3️⃣ Get top 5 (low fat/high protein/high fibre)\n"
    )

#   Flask Routes 
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    session_id = request.remote_addr  # Simple session tracking
    user_input = request.form['user_input']
    
    # Check if we're in the middle of a multi-step process
    if session_id in user_sessions:
        session_data = user_sessions[session_id]
        
        if session_data['mode'] == 'compare':
            if session_data['step'] == 1:
                session_data['food1'] = user_input
                session_data['step'] = 2
                return jsonify({
                    'status': 'success',
                    'response': "Got it! Now enter the second food item:",
                    'timestamp': datetime.now().strftime("%H:%M")
                })
            else:
                food2 = user_input
                comparison = compare_foods(session_data['food1'], food2)
                del user_sessions[session_id]
                
                if not comparison:
                    return jsonify({
                        'status': 'success',
                        'response': "❌ One or both foods not found.",
                        'timestamp': datetime.now().strftime("%H:%M")
                    })
                
                response = (
                    f"📊 Comparison:\n\n"
                    f"🔹 {comparison['food1']['name']}:\n"
                    f"   🔥 {comparison['food1']['energy']} kcal | 🍞 {comparison['food1']['carbs']}g | "
                    f"🥚 {comparison['food1']['protein']}g | 🧈 {comparison['food1']['fat']}g | 🌾 {comparison['food1']['fibre']}g\n"
                    f"\n🔹 {comparison['food2']['name']}:\n"
                    f"   🔥 {comparison['food2']['energy']} kcal | 🍞 {comparison['food2']['carbs']}g | "
                    f"🥚 {comparison['food2']['protein']}g | 🧈 {comparison['food2']['fat']}g | 🌾 {comparison['food2']['fibre']}g\n"
                    f"\n{comparison['key']}"
                )
                return jsonify({
                    'status': 'success',
                    'response': response,
                    'timestamp': datetime.now().strftime("%H:%M")
                })
        
        elif session_data['mode'] == 'top':
            if session_data['step'] == 1:
                if user_input.lower() not in ['food', 'beverages']:
                    return jsonify({
                        'status': 'success',
                        'response': "Please specify either 'food' or 'beverages'.",
                        'timestamp': datetime.now().strftime("%H:%M")
                    })
                session_data['category'] = user_input.lower()
                session_data['step'] = 2
                return jsonify({
                    'status': 'success',
                    'response': "Now choose nutrient type - 'low fat', 'high protein', or 'high fibre':",
                    'timestamp': datetime.now().strftime("%H:%M")
                })
            else:
                nutrient = user_input.lower()
                top_items = top_nutrient_items(session_data['category'], nutrient)
                del user_sessions[session_id]
                
                if not top_items:
                    return jsonify({
                        'status': 'success',
                        'response': "❌ Invalid nutrient type.",
                        'timestamp': datetime.now().strftime("%H:%M")
                    })
                
                response = f"Top 5 items for {nutrient.title()} in {top_items['category'].title()}:\n"
                for item in top_items['results']:
                    response += (
                        f"\n🍽️ {item['food_name']}:\n"
                        f"   🔥 Energy: {item['energy']} kcal\n"
                        f"   🧈 Fat: {item['fat']} g\n"
                        f"   🥚 Protein: {item['protein']} g\n"
                        f"   🌾 Fibre: {item['fibre']} g\n"
                    )
                
                return jsonify({
                    'status': 'success',
                    'response': response,
                    'timestamp': datetime.now().strftime("%H:%M")
                })
    
    # Check for general conversation
    general_response = handle_general_conversation(user_input, session_id)
    if general_response:
        return jsonify({
            'status': 'success',
            'response': general_response['response'],
            'timestamp': datetime.now().strftime("%H:%M")
        })
    
    # Default to food search
    results = search_excel(user_input)
    
    if not results:
        return jsonify({
            'status': 'success',
            'response': "❌ Sorry, I couldn't find that food item.",
            'timestamp': datetime.now().strftime("%H:%M")
        })
    
    responses = []
    for result in results:
        response = (
            f"🍽️ {result['food_name']}:\n"
            f"   🔥 Energy: {result['energy']} kcal\n"
            f"   🍞 Carbs: {result['carbs']} g\n"
            f"   🥚 Protein: {result['protein']} g\n"
            f"   🧈 Fat: {result['fat']} g\n"
            f"   🌾 Fibre: {result['fibre']} g"
        )
        responses.append(response)
    
    return jsonify({
        'status': 'success',
        'response': "\n\n".join(responses),
        'timestamp': datetime.now().strftime("%H:%M")
    })

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/debug_files')
def debug_files():
    import os
    from glob import glob
    
    # Check file existence and size
    def file_info(path):
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        return {
            'exists': exists,
            'size_bytes': size,
            'size_mb': round(size/(1024*1024), 2) if exists else 0,
            'modified_time': os.path.getmtime(path) if exists else None
        }
    
    # Find all Excel files in directory
    excel_files = {}
    for f in glob("*.xlsx"):
        excel_files[f] = file_info(f)
    
    return jsonify({
        'current_directory': os.getcwd(),
        'directory_contents': os.listdir('.'),
        'excel_files': excel_files,
        'loaded_food_columns': list(df_food.columns) if 'df_food' in globals() else 'Not loaded',
        'loaded_bev_columns': list(df_bev.columns) if 'df_bev' in globals() else 'Not loaded'
    })

@app.route('/reload_data')
def reload_data():
    global df_food, df_bev
    
    try:
        df_food = pd.read_excel("Modified_Nutrition_Data_No_Beverages.xlsx")
        df_bev = pd.read_excel("Beverages_Nutrition_Data.xlsx")
        
        # Normalize column names
        for df in [df_food, df_bev]:
            df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
            if 'food_name' in df.columns:
                df['food_name'] = df['food_name'].str.lower()
        
        return jsonify({
            'status': 'success',
            'food_sample': df_food.head(1).to_dict(),
            'bev_sample': df_bev.head(1).to_dict()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500