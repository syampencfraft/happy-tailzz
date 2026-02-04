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
        
        # Decode the results into a list of tuples (class, description, probability)
        decoded_preds = decode_predictions(preds, top=3)[0]

        # Filter for cat and dog breeds from ImageNet classes
        # ImageNet has many dog and cat breeds.
        results = []
        for _, label, score in decoded_preds:
            # ImageNet labels often have multiple names separated by commas (e.g., 'Entlebucher, Entlebucher_Sennenhund')
            # We take only the first one
            primary_name = label.split(',')[0]
            # Format the label (replace underscores with spaces and capitalize)
            breed_name = primary_name.replace('_', ' ').title()
            
            results.append({
                'breed': breed_name,
                'confidence': round(float(score) * 100, 2)
            })

        return results
    except Exception as e:
        print(f"Error during prediction: {e}")
        return None
