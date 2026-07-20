"""
Contest Mixin for WikiEval Application
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
        Store contest rules in a database-compatible JSON string.
        
        Parameters:
            rules_dict (dict): Contest rules to store. Invalid values are stored as empty rules.
        """
        # Convert dictionary to JSON string for database storage
        if isinstance(rules_dict, dict):
            self.rules = json.dumps(rules_dict)
        else:
            # Fallback to empty rules if invalid input
            self.rules = json.dumps({})


    def get_rules(self):
        """
        Retrieve the contest rules.
        
        Returns:
            dict: The decoded contest rules, or an empty dictionary when no valid rules are stored.
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
        Store jury member usernames as a comma-separated string.
        
        Parameters:
            jury_list (list): Jury member usernames to store. Non-list values clear the stored members.
        """
        # Convert list to comma-separated string for database storage
        if isinstance(jury_list, list):
            self.jury_members = ",".join(jury_list)
        else:
            self.jury_members = ""


    def get_jury_members(self):
        """
        Retrieve the contest's jury member usernames.
        
        Returns:
            list: Jury member usernames, or an empty list when none are stored.
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
        Store contest categories in a database-compatible JSON string.
        
        Parameters:
            categories_list (list): Category URLs to store. Non-list values are stored as an empty list.
        """
        # Convert list to JSON array string for database storage
        if isinstance(categories_list, list):
            self.categories = json.dumps(categories_list)
        else:
            self.categories = json.dumps([])


    def get_categories(self):
        """
        Retrieve the contest categories.
        
        Returns:
            list: The decoded categories, or an empty list when no valid categories are stored.
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
        Store scoring parameters as a JSON string, or clear them when no valid configuration is provided.
        
        Parameters:
            params (dict or None): Scoring configuration to store.
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
        Retrieve the contest's scoring parameters configuration.
        
        Returns:
            dict or None: The decoded scoring parameters, or `None` when no configuration is stored or the stored JSON is invalid.
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
        Store automated scoring settings for the contest.
        
        Parameters:
            settings (dict or None): Automated scoring configuration, or None to clear the settings.
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
        Retrieve the automated scoring settings configuration.
        
        Returns:
            dict or None: The decoded settings dictionary, or `None` when no valid configuration is stored.
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
        Store organizer usernames as a comma-separated string, ensuring the creator is included when available.
        
        Args:
            organizers_list: Organizer usernames to store.
            creator_username: Optional creator username to include in the stored organizers.
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
        Retrieve the contest's organizer usernames.
        
        Returns:
            list: Organizer usernames with surrounding whitespace removed and empty entries excluded.
        """
        if self.organizers:
            # Parse comma-separated string back to list
            return [
                username.strip()
                for username in self.organizers.split(",")
                if username.strip()
            ]
        return []
