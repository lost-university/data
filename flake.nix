{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-23.11";
    nixpkgs-unstable.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    inputs:
    inputs.flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = inputs.nixpkgs.legacyPackages.${system};
        pkgs-unstable = inputs.nixpkgs-unstable.legacyPackages.${system};
        pythonEnv = pkgs.python3.withPackages (ps: [
          ps.requests
          ps.lxml
        ]);
      in
      {
        devShells.default = pkgs.mkShell { nativeBuildInputs = [ pythonEnv ]; };
        formatter = pkgs-unstable.nixfmt-rfc-style;
      }
    );
}
