"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify it returns a dictionary
        assert isinstance(data, dict)
        
        # Verify all expected activities are present
        expected_activities = [
            "Soccer Team", "Basketball Club", "Art Studio", "Drama Club",
            "Science Club", "Debate Team", "Chess Club", "Programming Class", "Gym Class"
        ]
        for activity in expected_activities:
            assert activity in data
    
    def test_get_activities_contains_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_existing_activity_success(self, client):
        """Test successful signup for an existing activity"""
        response = client.post(
            "/activities/Soccer Team/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Signed up newstudent@mergington.edu for Soccer Team"
        
        # Verify student was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Soccer Team"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_signup_duplicate_email(self, client):
        """Test signing up with an email already registered"""
        # First signup
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "test@mergington.edu"}
        )
        
        # Try to signup again with same email
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up for this activity"
    
    def test_signup_preserves_existing_participants(self, client):
        """Test that signup doesn't remove existing participants"""
        # Get initial participants
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()["Drama Club"]["participants"].copy()
        
        # Add new participant
        client.post(
            "/activities/Drama Club/signup",
            params={"email": "newcomer@mergington.edu"}
        )
        
        # Verify all participants are still there
        final_response = client.get("/activities")
        final_participants = final_response.json()["Drama Club"]["participants"]
        
        for participant in initial_participants:
            assert participant in final_participants
        assert "newcomer@mergington.edu" in final_participants


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/remove endpoint"""
    
    def test_remove_existing_participant_success(self, client):
        """Test successful removal of an existing participant"""
        # First add a participant
        client.post(
            "/activities/Art Studio/signup",
            params={"email": "temp@mergington.edu"}
        )
        
        # Now remove them
        response = client.delete(
            "/activities/Art Studio/remove",
            params={"email": "temp@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Removed temp@mergington.edu from Art Studio"
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "temp@mergington.edu" not in activities_data["Art Studio"]["participants"]
    
    def test_remove_from_nonexistent_activity(self, client):
        """Test removing participant from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Fake Activity/remove",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_remove_nonexistent_participant(self, client):
        """Test removing a participant who isn't registered"""
        response = client.delete(
            "/activities/Science Club/remove",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Student not found in this activity"
    
    def test_remove_does_not_affect_other_participants(self, client):
        """Test that removing one participant doesn't affect others"""
        # Get initial participants
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()["Basketball Club"]["participants"].copy()
        
        # Remove one participant
        participant_to_remove = initial_participants[0]
        client.delete(
            "/activities/Basketball Club/remove",
            params={"email": participant_to_remove}
        )
        
        # Verify other participants remain
        final_response = client.get("/activities")
        final_participants = final_response.json()["Basketball Club"]["participants"]
        
        assert participant_to_remove not in final_participants
        for participant in initial_participants[1:]:
            assert participant in final_participants


class TestIntegrationScenarios:
    """Integration tests for complete workflows"""
    
    def test_full_signup_and_removal_workflow(self, client):
        """Test complete workflow: get activities, signup, verify, remove, verify"""
        # 1. Get initial activities
        initial_response = client.get("/activities")
        assert initial_response.status_code == 200
        initial_count = len(initial_response.json()["Debate Team"]["participants"])
        
        # 2. Sign up for an activity
        signup_response = client.post(
            "/activities/Debate Team/signup",
            params={"email": "workflow@mergington.edu"}
        )
        assert signup_response.status_code == 200
        
        # 3. Verify signup
        after_signup_response = client.get("/activities")
        after_signup_count = len(after_signup_response.json()["Debate Team"]["participants"])
        assert after_signup_count == initial_count + 1
        assert "workflow@mergington.edu" in after_signup_response.json()["Debate Team"]["participants"]
        
        # 4. Remove participant
        remove_response = client.delete(
            "/activities/Debate Team/remove",
            params={"email": "workflow@mergington.edu"}
        )
        assert remove_response.status_code == 200
        
        # 5. Verify removal
        final_response = client.get("/activities")
        final_count = len(final_response.json()["Debate Team"]["participants"])
        assert final_count == initial_count
        assert "workflow@mergington.edu" not in final_response.json()["Debate Team"]["participants"]
    
    def test_multiple_signups_different_activities(self, client):
        """Test that a student can sign up for multiple activities"""
        student_email = "multisport@mergington.edu"
        
        # Sign up for multiple activities
        activities = ["Soccer Team", "Chess Club", "Programming Class"]
        for activity in activities:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": student_email}
            )
            assert response.status_code == 200
        
        # Verify student is in all activities
        all_activities_response = client.get("/activities")
        all_activities_data = all_activities_response.json()
        
        for activity in activities:
            assert student_email in all_activities_data[activity]["participants"]
