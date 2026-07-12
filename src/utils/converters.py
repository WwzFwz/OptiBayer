"""Fungsi konversi unit."""

def ton_to_liters(cao_ton: float, density: float = 1.2, concentration: float = 0.25) -> float:
    """
    Konversi dosis CaO dari ton (padat) ke Liter slurry.
    Formula: L = (ton * 1000) / (density * concentration)
    
    Parameters:
        cao_ton (float): Dosis CaO dalam ton
        density (float): Massa jenis slurry dalam kg/L (default 1.2 kg/L)
        concentration (float): Fraksi konsentrasi padatan dalam slurry (default 25% atau 0.25)
        
    Returns:
        float: Volume slurry dalam Liter
    """
    if concentration <= 0 or density <= 0:
        return 0.0
    return (cao_ton * 1000.0) / (density * concentration)
