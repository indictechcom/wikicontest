"""
Contest Mixin for WikiContest Application
Contains shared methods for Contest and ContestRequest models
This eliminates code duplication between the two models
"""

import json


# ------------------------------------------------------------------------
# CONTEST MIXIN
# ------------------------------------------------------------------------

class ContestMixin:
    """
    Mixin class providing shared methods for Contest and ContestRequest models
    
    This mixin contains methods for handling:
    - Rules (JSON dictionary storage)
    - Jury members (comma-separated string storage)
    - Categories (JSON array storage)
    - Scoring parameters (JSON dictionary storage)
    - Organizers (comma-separated string storage)
    
    Both Contest and ContestRequest inherit from this mixin to avoid code duplication
    """

    # ------------------------------------------------------------------------
    # RULES MANAGEMENT (JSON Dictionary Storage)
    # ------------------------------------------------------------------------

    def set_rules(self, rules_dict):
        """
        Set contest rules from dictionary

        Args:
            rules_dict: Dictionary containing contest rules
        """
        # Convert dictionary to JSON string for database storage
        if isinstance(rules_dict, dict):
            self.rules = json.dumps(rules_dict)
        else:
            # Fallback to empty rules if invalid input
            self.rules = json.dumps({})


    def get_rules(self):
        """
        Get contest rules as dictionary

        Returns:
            dict: Contest rules dictionary
        """
        if self.rules:
            try:
                # Parse JSON string back to dictionary
                return json.loads(self.rules)
            except json.JSONDecodeError:
                # Return empty dict if JSON is corrupted
                return {}
        return {}


    # ------------------------------------------------------------------------
    # JURY MEMBERS MANAGEMENT (Comma-Separated Storage)
    # ------------------------------------------------------------------------

    def set_jury_members(self, jury_list):
        """
        Set jury members from list

        Args:
            jury_list: List of jury member usernames
        """
        # Convert list to comma-separated string for database storage
        if isinstance(jury_list, list):
            self.jury_members = ",".join(jury_list)
        else:
            self.jury_members = ""


    def get_jury_members(self):
        """
        Get jury members as list

        Returns:
            list: List of jury member usernames
        """
        if self.jury_members:
            # Parse comma-separated string back to list
            # Strip whitespace and filter empty strings
            return [
                username.strip()
                for username in self.jury_members.split(",")
                if username.strip()
            ]
        return []


    # ------------------------------------------------------------------------
    # CATEGORIES MANAGEMENT (JSON Array Storage)
    # ------------------------------------------------------------------------

    def set_categories(self, categories_list):
        """
        Set contest categories from list

        Args:
            categories_list: List of category URLs
        """
        # Convert list to JSON array string for database storage
        if isinstance(categories_list, list):
            self.categories = json.dumps(categories_list)
        else:
            self.categories = json.dumps([])


    def get_categories(self):
        """
        Get contest categories as list

        Returns:
            list: List of category URLs
        """
        if self.categories:
            try:
                # Parse JSON array string back to list
                return json.loads(self.categories)
            except json.JSONDecodeError:
                # Return empty list if JSON is corrupted
                return []
        return []


    # ------------------------------------------------------------------------
    # SCORING PARAMETERS MANAGEMENT (JSON Dictionary Storage)
    # ------------------------------------------------------------------------

    def set_scoring_parameters(self, params):
        """
        Set scoring parameters configuration

        Args:
            params: Dict or None containing scoring configuration
        """
        if params is None:
            self.scoring_parameters = None
        elif isinstance(params, dict):
            # Store as JSON string
            self.scoring_parameters = json.dumps(params)
        else:
            self.scoring_parameters = None


    def get_scoring_parameters(self):
        """
        Get scoring parameters configuration

        Returns:
            dict or None: Scoring parameters configuration
        """
        if not self.scoring_parameters:
            return None
        try:
            # Parse JSON string back to dictionary
            return json.loads(self.scoring_parameters)
        except json.JSONDecodeError:
            return None


    # ------------------------------------------------------------------------
    # AUTOMATED SETTINGS MANAGEMENT (JSON Dictionary Storage)
    # ------------------------------------------------------------------------

    def set_automated_settings(self, settings):
        """
        Set automated scoring settings configuration

        Args:
            settings: Dict or None containing automated scoring configuration
                {
                    "enabled": true,
                    "eligibility": {
                        "min_edits": 100,
                        "min_outgoing_links": 3
                    },
                    "evaluation": {
                        "points_per_accepted": 10,
                        "points_per_byte": 0.001,
                        "points_per_incoming_link": 2,
                        "points_per_outgoing_link": 1,
                        "points_per_category": 1,
                        "points_per_new_reference": 3,
                        "points_per_reused_reference": 1,
                        "points_per_infobox": 5,
                        "points_per_image": 2
                    }
                }
        """
        if settings is None:
            self.automated_settings = None
        elif isinstance(settings, dict):
            # Store as JSON string
            self.automated_settings = json.dumps(settings)
        else:
            self.automated_settings = None


    def get_automated_settings(self):
        """
        Get automated scoring settings configuration

        Returns:
            dict or None: Automated scoring settings configuration
        """
        if not self.automated_settings:
            return None
        try:
            # Parse JSON string back to dictionary
            return json.loads(self.automated_settings)
        except json.JSONDecodeError:
            return None


    # ------------------------------------------------------------------------
    # ORGANIZERS MANAGEMENT (Comma-Separated Storage)
    # ------------------------------------------------------------------------

    def set_organizers(self, organizers_list, creator_username=None):
        """
        Set organizers from list. Creator is always included if provided.

        Args:
            organizers_list: List of organizer usernames
            creator_username: Username of creator (auto-added if provided)
        """
        if isinstance(organizers_list, list):
            # Remove duplicates and empty strings
            unique_organizers = list({
                username.strip()
                for username in organizers_list
                if username and username.strip()
            })

            # Ensure creator is always in the organizers list if provided
            if creator_username:
                creator_username = creator_username.strip()
                if creator_username and creator_username not in unique_organizers:
                    # Add creator at the beginning
                    unique_organizers.insert(0, creator_username)
            elif hasattr(self, 'created_by') and self.created_by:
                # Fallback to created_by if no creator_username provided
                creator = self.created_by.strip()
                if creator and creator not in unique_organizers:
                    unique_organizers.insert(0, creator)

            # Convert list to comma-separated string
            self.organizers = ",".join(unique_organizers)
        else:
            # Fallback: set to creator only if invalid input
            if creator_username:
                self.organizers = creator_username.strip()
            elif hasattr(self, 'created_by') and self.created_by:
                self.organizers = self.created_by.strip()
            else:
                self.organizers = ""


    def get_organizers(self):
        """
        Get organizers as list of usernames.

        Returns:
            list: List of organizer usernames
        """
        if self.organizers:
            # Parse comma-separated string back to list
            return [
                username.strip()
                for username in self.organizers.split(",")
                if username.strip()
            ]
        return []
