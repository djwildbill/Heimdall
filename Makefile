PACKER_VERSION=1.7.2
HEIMDALL_HOSTNAME=heimdall
HEIMDALL_BRANCH=heimdall-dev
HEIMDALL_VERSION=0.1.0-alpha

all: clean install heimdall

langs:
	@for lang in pwnagotchi/locale/*/; do\
		echo "compiling language: $$lang ..."; \
		./scripts/language.sh compile $$(basename $$lang); \
	done

install:
	curl https://releases.hashicorp.com/packer/$(PACKER_VERSION)/packer_$(PACKER_VERSION)_linux_amd64.zip -o /tmp/packer.zip
	unzip /tmp/packer.zip -d /tmp
	sudo mv /tmp/packer /usr/bin/packer
	git clone https://github.com/solo-io/packer-builder-arm-image /tmp/packer-builder-arm-image
	cd /tmp/packer-builder-arm-image && go get -d ./... && go build
	sudo cp /tmp/packer-builder-arm-image/packer-builder-arm-image /usr/bin

heimdall:
	cd builder && sudo /usr/bin/packer build \
		-var "pwn_hostname=$(HEIMDALL_HOSTNAME)" \
		-var "pwn_version=$(HEIMDALL_BRANCH)" \
		pwnagotchi.json
	sudo mv builder/output-pwnagotchi/image Heimdall-v$(HEIMDALL_VERSION).img
	sudo sha256sum Heimdall-v$(HEIMDALL_VERSION).img > Heimdall-v$(HEIMDALL_VERSION).sha256
	sudo zip Heimdall-v$(HEIMDALL_VERSION).zip \
		Heimdall-v$(HEIMDALL_VERSION).sha256 \
		Heimdall-v$(HEIMDALL_VERSION).img

# Compatibility alias for the upstream build command.
image: heimdall

clean:
	rm -rf /tmp/packer-builder-arm-image
	rm -f Heimdall-v*.zip Heimdall-v*.img Heimdall-v*.sha256
	rm -f pwnagotchi-raspbian-lite-*.zip pwnagotchi-raspbian-lite-*.img pwnagotchi-raspbian-lite-*.sha256
	rm -rf builder/output-pwnagotchi builder/packer_cache
