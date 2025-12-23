{
  description = "Rawji - Fujifilm RAW Conversion Tool - Convert RAF files using in-camera processing via USB";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        rawji = pkgs.python3Packages.buildPythonApplication {
          pname = "rawji";
          version = "0.1.0";
          format = "pyproject";

          src = ./.;

          nativeBuildInputs = with pkgs.python3Packages; [
            setuptools
            wheel
          ];

          propagatedBuildInputs = with pkgs.python3Packages; [
            pyusb
          ];

          meta = with pkgs.lib; {
            description = "Rawji - Fujifilm RAW Conversion Tool - Convert RAF files using in-camera processing via USB";
            homepage = "https://github.com/pinpox/rawji";
            license = licenses.gpl3Plus;
            maintainers = [ ];
            mainProgram = "rawji";
          };
        };
      in
      {
        packages = {
          default = rawji;
          rawji = rawji;
        };

        apps = {
          default = {
            type = "app";
            program = "${rawji}/bin/rawji";
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            pkgs.python3
            pkgs.python3Packages.pyusb
            pkgs.python3Packages.setuptools
            pkgs.python3Packages.wheel
          ];

          shellHook = ''
            echo "Rawji - Fujifilm RAW Conversion Tool development environment"
            echo "Run: python -m rawji <args> to test the tool"
          '';
        };
      }
    );
}
