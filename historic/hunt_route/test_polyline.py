import polyline


if __name__ == "__main__":
    coordinates = [
        [11.1022361, 46.060613], 
        [11.1188586, 46.0627946] 
    ]

    # You can encode from (lon, lat) tuples by setting geojson=True.
    short_poly = polyline.encode(coordinates, geojson=True)
    print(short_poly) 
    # yecxG_lwbAsL{fB
    # the straight line connecting the two coordinates
    
    long_poly = "ghcxG_ewbAgASeA[Uh@W|@Ul@QzAINm@t@i@b@c@PaBr@UP[XO\\AX@jB@^Bb@@X@RgFVa@DG]Io@I[_@s@{@{AEC@IAICOCGEMAAE?IIo@FYIYs@OMMAGH@t@DTQx@s@p@YP_ALy@n@IAMJWHSPQBu@\\YT[ZQJk@L_@A]Ho@b@UH]h@KINY\\oAPa@FQDKNo@?SPu@Eo@Ie@]}@W]MGQQ?YF]Ge@mA_CaA_CMMEQUyAIS[wAQuABe@XqBl@sA\\u@Pw@n@sAnAqBb@]HOFITWr@i@XOHGd@_@`@q@^_BDW@IGSWYm@CKIc@@cBjAgAN]Li@Jk@Aa@GUEC?c@ASLGJYx@KZCDGBEIA[DeBCUECg@Zw@rAORc@XkAd@mBzBc@Tc@JOA[@C?CAP{@Jc@NU~@{@HONk@BUDq@DWH[|AcBv@cAZi@j@oAFMJWx@iBFQL[Pg@BI\\qAHg@@IBO@MHcA@mAAm@CYG]G_@CKSeACOEa@?KAM@k@\\gAZw@RSNQD?DCDEDY?IAGCEACCCDW@A`AuF@CFDPFv@\\l@VdDvAn@Xl@RND@{@NIN?bDrALFBOxBx@Ac@QyDGkASqE@K?KE{@AQ?YIwA?IAEOgDAUPCjAOVCZEDAnBUNCbAOj@Ih@KJAF?`@GHAr@KB?HBND`@b@FDl@b@`@VJB?PD?P@^C"
    # You can decode into (lon, lat) tuples by setting geojson=True.
    coordinates = polyline.decode(long_poly, geojson=True) 
    print(coordinates)    
    # many coordinates:
    # [ (11.10112, 46.061), (11.10122, 46.06136), ..., (11.11895, 46.06296), (11.11897, 46.0628)]
    