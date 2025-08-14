flake: { config, pkgs, lib, ... }:

with lib;

let
  cfg = config.services.kartograf;
  postScript = pkgs.writeScriptBin "post-script" /* bash */ ''
    #!/${pkgs.bash}/bin/bash
    timestamp=$(${pkgs.findutils}/bin/find out -mindepth 1 -maxdepth 1 -type d | ${pkgs.coreutils}/bin/cut -d/ -f2)
    mv out/$timestamp/final_result.txt ${cfg.resultPath}/asmap-$timestamp.txt
    echo "Copied result from /out/$timestamp/final_result.txt to ${cfg.resultPath}/asmap-$timestamp.txt"
    rm -rf out
    echo "Cleaned up temporary directories."
  '';
in
{
  options.services.kartograf = {
    enable = mkEnableOption "kartograf";
    package = mkOption {
      type = types.package;
      default = (flake.packages.${pkgs.stdenv.hostPlatform.system}).kartograf;
      description = mdDoc "kartograf binary to use";
    };
    wipeDataDir = mkEnableOption "delete data directory (inputs to the final map)" // { default = true; };
    useIRR = mkEnableOption "using Internet Routing Registry (IRR) data" // { default = true; };
    useRV = mkEnableOption "using RouteViews (RV) data" // { default = true; };
    debug = mkEnableOption "enable debug, retaining output files and debug.log" // { default = false; };
    runPostScript = mkEnableOption "delete all temporary files, and put final result in /home/kartograf dir" // { default = true; };
    schedule = mkOption {
      type = types.str;
      default = "*-*-01 00:00:00 UTC";
      example = "monthly";
      description = mdDoc "Systemd OnCalendar setting for kartograf.";
    };
    resultPath = mkOption {
      type = types.path;
      default = "/home/kartograf/";
      example = "/scratch/results/kartograf/";
      description = mdDoc "Directory for results.";
    };
  };

  config = mkIf cfg.enable {
    users = {
      users.kartograf = {
        isSystemUser = true;
        group = "kartograf";
        home = "/home/kartograf";
        createHome = true;
        homeMode = "755";
      };
      groups.kartograf = { };
    };

    systemd.timers.kartograf = {
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnCalendar = cfg.schedule;
        Unit = [ "kartograf.service" ];
      };
    };

    systemd.services.kartograf = {
      description = "kartograf";
      after = [ "network-online.target" ];
      serviceConfig = {
        Environment = "PYTHONUNBUFFERED=1";
        ExecStopPost = let
          postScriptBin = "${postScript}/bin/post-script";
        in "${optionalString cfg.runPostScript postScriptBin }";
        ExecStart = ''${cfg.package}/bin/kartograf map \
          ${optionalString cfg.wipeDataDir "--wipe_data_dir" } \
          ${optionalString cfg.useIRR "--irr" } \
          ${optionalString cfg.useRV "--routeviews" } \
          ${optionalString cfg.debug "--debug" }
        '';
        MemoryDenyWriteExecute = true;
        WorkingDirectory = cfg.resultPath;
        ReadWriteDirectories = cfg.resultPath;
        User = "kartograf";
        Group = "kartograf";
      };
    };
  };
}
