import numpy as np
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input, decode_predictions
from tensorflow.keras.preprocessing import image
import tensorflow as tf

# Load the pre-trained MobileNetV2 model
# This will download the weights (about 14MB) if not already present
model = MobileNetV2(weights='imagenet')

def predict_pet_breed(img_path):
    """
    Predicts the breed of a pet from an image using MobileNetV2.
    """
    try:
        # Load and preprocess the image
        img = image.load_img(img_path, target_size=(224, 224))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        # Make prediction
        preds = model.predict(img_array)
        
        # Check if the top prediction is a cat or dog
        # ImageNet indices: 
        # 151-268: Dogs
        # 281-285: Cats
        top_index = np.argmax(preds)
        
        is_dog = 151 <= top_index <= 268
        is_cat = 281 <= top_index <= 285
        
        if not (is_dog or is_cat):
            return {'error': 'Invalid Image: No cat or dog detected. Please upload a clear image of a pet.'}

        # Decode the results into a list of tuples (class, description, probability)
        decoded_preds = decode_predictions(preds, top=3)[0]

        # Get the top valid result
        results = []
        for _, label, score in decoded_preds:
            primary_name = label.split(',')[0]
            breed_name = primary_name.replace('_', ' ').title()
            
            results.append({
                'breed': breed_name,
                'confidence': round(float(score) * 100, 2)
            })

        return results
    except Exception as e:
        print(f"Error during prediction: {e}")
        return None
