from historic.hunt_route import api_google

def fine_tuning_trento_open(profile, circular_route, duration_min):        
    if circular_route:
        if profile == api_google.PROFILE_FOOT_WALKING:
            if duration_min < 60:
                max_grid_overalapping = 100
                duration_tolerance_min = 10
            else:
                max_grid_overalapping = duration_min/30 * 100
                duration_tolerance_min = duration_min/30 * 20
        else:
            # bicycle
            max_grid_overalapping = duration_min/30 * 50
            duration_tolerance_min = duration_min/30 * 5            
                
    else:
        # linear
        if profile == api_google.PROFILE_FOOT_WALKING:
            max_grid_overalapping = 20
            duration_tolerance_min = 3 * duration_min/30
        else: 
            # bicycle
            max_grid_overalapping = duration_min/30 * 20
            duration_tolerance_min = duration_min/30 * 8

    return max_grid_overalapping, duration_tolerance_min