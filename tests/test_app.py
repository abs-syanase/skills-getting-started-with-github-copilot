"""
Tests for the Mergington High School API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        activity: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for activity, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for activity_name, details in original_activities.items():
        if activity_name in activities:
            activities[activity_name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_index(self, client):
        """Test that root endpoint redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the activities endpoint"""
    
    def test_get_activities(self, client):
        """Test fetching all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check structure of first activity
        first_activity = next(iter(data.values()))
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
    
    def test_activities_have_expected_fields(self, client):
        """Test that each activity has all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert isinstance(activity_name, str)
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)
            assert isinstance(activity_details["max_participants"], int)


class TestSignupEndpoint:
    """Tests for the signup endpoint"""
    
    def test_signup_for_activity_success(self, client):
        """Test successful signup for an activity"""
        activity_name = "Soccer Team"
        email = "newstudent@mergington.edu"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify student was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post("/activities/Nonexistent Activity/signup?email=test@mergington.edu")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_duplicate_student(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        activity_name = "Soccer Team"
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response2.status_code == 400
        
        data = response2.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity names"""
        # Using Art Club which has a space
        activity_name = "Art Club"
        email = "artist@mergington.edu"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200


class TestUnregisterEndpoint:
    """Tests for the unregister endpoint"""
    
    def test_unregister_from_activity_success(self, client):
        """Test successful unregistration from an activity"""
        activity_name = "Soccer Team"
        email = "alex@mergington.edu"  # Already signed up
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregister from an activity that doesn't exist"""
        response = client.delete("/activities/Nonexistent Activity/unregister?email=test@mergington.edu")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_unregister_student_not_signed_up(self, client):
        """Test unregistering a student who is not signed up"""
        activity_name = "Soccer Team"
        email = "notsignedup@mergington.edu"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert "not signed up" in data["detail"].lower()
    
    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow of signing up and unregistering"""
        activity_name = "Drama Club"
        email = "workflow@mergington.edu"
        
        # Sign up
        signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
        
        # Unregister
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        activities_response2 = client.get("/activities")
        activities_data2 = activities_response2.json()
        assert email not in activities_data2[activity_name]["participants"]


class TestActivityCapacity:
    """Tests for activity capacity limits"""
    
    def test_activity_has_max_participants_limit(self, client):
        """Test that activities have a max_participants limit"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_details in data.values():
            assert activity_details["max_participants"] > 0
            assert len(activity_details["participants"]) <= activity_details["max_participants"]
