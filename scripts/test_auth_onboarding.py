import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.stdout.reconfigure(encoding='utf-8')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

import uuid
print('=== Test 1: Register Normal User ===')
test_email = f"test_onboard_{uuid.uuid4().hex[:8]}@nutrix.io"
reg_payload = {
    'name': 'Test New User',
    'email': test_email,
    'password': 'password123',
    'age': 28,
    'gender': 'female',
    'height': 165.0,
    'weight': 62.0,
    'activity_level': 'lightly_active',
    'goal': 'fat loss',
    'preferences': [{'preference_type': 'diet_type', 'value': 'Vegetarian'}]
}
res_reg = client.post('/api/auth/register', json=reg_payload)
print('Register status:', res_reg.status_code)
if res_reg.status_code == 400 and 'already exists' in res_reg.text:
    print('User already exists, proceeding to login test.')
else:
    assert res_reg.status_code == 201, f"Expected 201, got {res_reg.status_code}: {res_reg.text}"
    reg_data = res_reg.json()
    print('is_new_user:', reg_data.get('is_new_user'))
    print('is_onboarded in user profile:', reg_data['user'].get('is_onboarded'))
    assert reg_data.get('is_new_user') == True, "New registered user must have is_new_user=True"
    assert reg_data['user'].get('is_onboarded') == False, "New registered user must have is_onboarded=False before onboarding"

print('\n=== Test 2: Normal Login for Un-onboarded User ===')
res_login = client.post('/api/auth/login', json={'email': test_email, 'password': 'password123'})
assert res_login.status_code == 200
login_data = res_login.json()
print('Login is_onboarded:', login_data['user'].get('is_onboarded'))
assert login_data['user'].get('is_onboarded') == False, "Un-onboarded user must return is_onboarded=False on login"

print('\n=== Test 3: Complete Onboarding via /calculate-profile ===')
headers = {'Authorization': f"Bearer {login_data['access_token']}"}
onboard_payload = {
    'name': 'Test New User',
    'email': test_email,
    'age': 28,
    'gender': 'female',
    'height': 165.0,
    'weight': 62.0,
    'activity_level': 'lightly_active',
    'goal': 'fat loss',
    'water_target_ml': 2200.0,
    'preferences': [
        {'preference_type': 'diet_type', 'value': 'Vegetarian'},
        {'preference_type': 'like', 'value': 'oats'},
        {'preference_type': 'like', 'value': 'paneer'},
        {'preference_type': 'allergy', 'value': 'peanuts'},
        {'preference_type': 'dislike', 'value': 'bitter gourd'}
    ]
}
res_onboard = client.post('/calculate-profile', json=onboard_payload, headers=headers)
print('Calculate-profile status:', res_onboard.status_code)
assert res_onboard.status_code in (200, 201), f"Expected 200 or 201, got {res_onboard.status_code}: {res_onboard.text}"
onboard_data = res_onboard.json()
print('Onboarded response is_onboarded:', onboard_data.get('is_onboarded'))
print('Likes:', onboard_data.get('likes'))
print('Allergies:', onboard_data.get('allergies'))
print('Dislikes:', onboard_data.get('dislikes'))
assert onboard_data.get('is_onboarded') == True, "User must now have is_onboarded=True"
assert 'peanuts' in onboard_data.get('allergies'), "Allergies must be saved"
assert 'oats' in onboard_data.get('likes'), "Likes must be saved"

print('\n=== Test 4: Subsequent Login for Onboarded User ===')
res_login2 = client.post('/api/auth/login', json={'email': test_email, 'password': 'password123'})
assert res_login2.status_code == 200
login2_data = res_login2.json()
print('Login 2 is_onboarded:', login2_data['user'].get('is_onboarded'))
assert login2_data['user'].get('is_onboarded') == True, "Onboarded user must return is_onboarded=True on subsequent logins"

print('\nALL ONBOARDING TESTS PASSED!')
